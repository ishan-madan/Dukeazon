from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
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
@login_required
def seller_inventory(seller_id):
    """
    Render a seller's inventory as an HTML page.
    """
    # Check if user is the seller or is authorized to view this inventory
    if current_user.id != seller_id:
        flash('You do not have permission to access this inventory.')
        return redirect(url_for('index.index'))
    
    # Fetch all listings for this seller
    inventory = ProductSeller.get_all_detailed_by_seller(seller_id)
    add_form = AddProductForm()

    return render_template('seller_inventory.html', inventory=inventory, add_form=add_form)


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
            # Check if seller already has this product
            existing = ProductSeller.get_all_by_seller(seller_id)
            if any(p.product_id == form.product_id.data for p in existing):
                flash('This product is already in your inventory. Use Update to change quantity.')
            else:
                ProductSeller.add(seller_id, form.product_id.data, 
                                form.price.data, form.quantity.data)
                # Ensure product is marked available when a seller lists it
                Product.set_available(form.product_id.data, True)
                flash('Product added to inventory successfully!')
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
            # After updating quantity, set product availability based on whether any
            # active listings with quantity > 0 remain for this product.
            has_active = ProductSeller.has_active_listings_for_product(listing.product_id)
            Product.set_available(listing.product_id, has_active)
            flash('Quantity updated successfully!')
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
            # Toggle active state: deactivate if active, activate if inactive
            if listing.is_active:
                ProductSeller.deactivate(listing_id)
                # if no remaining active listings for this product, mark product unavailable
                if not ProductSeller.has_active_listings_for_product(listing.product_id):
                    Product.set_available(listing.product_id, False)
                flash('Product removed from inventory.')
            else:
                ProductSeller.activate(listing_id)
                # ensure product available when re-listed
                Product.set_available(listing.product_id, True)
                flash('Product re-listed successfully.')
        except Exception as e:
            flash(f'Error removing product: {str(e)}')
    
    return redirect(url_for('product_seller.seller_inventory', seller_id=seller_id))
