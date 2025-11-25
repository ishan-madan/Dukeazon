from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app as app
from flask_login import current_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from .models.product_seller import ProductSeller
from .models.product import Product

bp = Blueprint('product_seller', __name__, url_prefix='/sellers')


class AddProductForm(FlaskForm):
    product_id = IntegerField('Product ID', validators=[DataRequired(), NumberRange(min=1)])
    price = DecimalField('Price', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Product')

    def validate_product_id(self, field):
        product = Product.get(field.data)
        if not product:
            raise ValidationError('Product ID does not exist.')


class UpdateQuantityForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Update')


class RemoveProductForm(FlaskForm):
    submit = SubmitField('Remove from Inventory')


@bp.route('/<int:seller_id>/inventory')
def seller_inventory(seller_id):
    """
    Render a seller's inventory as an HTML page.
    """
                                                                         
    if current_user.id != seller_id:
        flash('You do not have permission to access this inventory.')
        return redirect(url_for('index.index'))
    
                                        
    inventory = ProductSeller.get_all_detailed_by_seller(seller_id)

    # seller basic info 
    seller_rows = app.db.execute("""
        SELECT id, firstname, lastname
        FROM Users
        WHERE id = :sid
    """, sid=seller_id)
    seller = seller_rows[0] if seller_rows else None

    # rating summary for this seller
    rating_rows = app.db.execute("""
        SELECT
            AVG(rating) AS avg_rating,
            COUNT(*)   AS num_reviews
        FROM seller_reviews
        WHERE seller_id = :sid
    """, sid=seller_id)
    seller_rating = rating_rows[0] if rating_rows else None

    # full list of reviews for this seller
    seller_reviews = app.db.execute("""
        SELECT
            sr.rating,
            sr.body,
            sr.created_at,
            u.firstname,
            u.lastname
        FROM seller_reviews sr
        JOIN Users u ON u.id = sr.user_id
        WHERE sr.seller_id = :sid
        ORDER BY sr.created_at DESC
    """, sid=seller_id)
                                                             
    inventory = sorted(inventory, key=lambda itm: itm.get('product_id', 0))
    add_form = AddProductForm()

                                                                              
    try:
        analytics = ProductSeller.analytics_for_seller(seller_id, days=30, limit=6)
    except Exception:
        analytics = None

    return render_template('seller_inventory.html', inventory=inventory, add_form=add_form, analytics=analytics)


@bp.route('/<int:seller_id>/inventory/add', methods=['POST'])
@login_required
def add_product(seller_id):
    """
    Add a new product to seller's inventory.
    """
    if current_user.id != seller_id:
        flash('You do not have permission to perform this action.')
        return redirect(url_for('index.index'))
    
    
    
    form = AddProductForm()
    if form.validate_on_submit():
        try:
                                                      
            existing = ProductSeller.get_all_by_seller(seller_id)
            if any(p.product_id == form.product_id.data for p in existing):
                flash('This product is already in your inventory. Use Update to change quantity.', 'warning')
            else:
                ProductSeller.add(seller_id, form.product_id.data, 
                                form.price.data, form.quantity.data)
                                                                           
                Product.set_available(form.product_id.data, True)
                flash('Product added to inventory successfully!', 'success')
        except Exception as e:
            flash(f'Error adding product: {str(e)}')
    
    return redirect(url_for('product_seller.seller_inventory', seller_id=seller_id))


@bp.route('/<int:seller_id>/inventory/<int:listing_id>/update', methods=['POST'])
@login_required
def update_product(seller_id, listing_id):
    """
    Update quantity for a product in seller's inventory.
    """
    if current_user.id != seller_id:
        flash('You do not have permission to perform this action.')
        return redirect(url_for('index.index'))
    
    listing = ProductSeller.get(listing_id)
    if not listing or listing.seller_id != seller_id:
        flash('Listing not found.')
        return redirect(url_for('product_seller.seller_inventory', seller_id=seller_id))
    
    form = UpdateQuantityForm()
    if form.validate_on_submit():
        try:
            ProductSeller.update_quantity(listing_id, form.quantity.data)
                                                                                    
                                                                        
            has_active = ProductSeller.has_active_listings_for_product(listing.product_id)
            Product.set_available(listing.product_id, has_active)
            flash('Quantity updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating quantity: {str(e)}')
    
    return redirect(url_for('product_seller.seller_inventory', seller_id=seller_id))


@bp.route('/<int:seller_id>/inventory/<int:listing_id>/remove', methods=['POST'])
@login_required
def remove_product(seller_id, listing_id):
    """
    Remove a product from seller's inventory (soft delete).
    """
    if current_user.id != seller_id:
        flash('You do not have permission to perform this action.')
        return redirect(url_for('index.index'))
    
    listing = ProductSeller.get(listing_id)
    if not listing or listing.seller_id != seller_id:
        flash('Listing not found.')
        return redirect(url_for('product_seller.seller_inventory', seller_id=seller_id))
    
    form = RemoveProductForm()
    if form.validate_on_submit():
        try:
                                                                             
            if listing.is_active:
                ProductSeller.deactivate(listing_id)
                                                                                            
                if not ProductSeller.has_active_listings_for_product(listing.product_id):
                    Product.set_available(listing.product_id, False)
                flash('Product removed from inventory.', 'success')
            else:
                ProductSeller.activate(listing_id)
                                                         
                Product.set_available(listing.product_id, True)
                flash('Product re-listed successfully.', 'success')
        except Exception as e:
            flash(f'Error removing product: {str(e)}')
    
    return redirect(url_for('product_seller.seller_inventory', seller_id=seller_id))
