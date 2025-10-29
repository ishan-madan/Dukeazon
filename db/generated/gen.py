from werkzeug.security import generate_password_hash
import csv
from faker import Faker

num_users = 100
num_products = 2000
num_purchases = 2500

Faker.seed(0)
fake = Faker()


def get_csv_writer(f):
    return csv.writer(f, dialect='unix')


def gen_users(num_users):
    with open('Users.csv', 'w') as f:
        writer = get_csv_writer(f)
        print('Users...', end=' ', flush=True)
        for uid in range(num_users):
            if uid % 10 == 0:
                print(f'{uid}', end=' ', flush=True)
            profile = fake.profile()
            email = profile['mail']
            plain_password = f'pass{uid}'
            password = generate_password_hash(plain_password)
            name_components = profile['name'].split(' ')
            firstname = name_components[0]
            lastname = name_components[-1]
            writer.writerow([uid, email, password, firstname, lastname])
        print(f'{num_users} generated')
    return


def gen_products(num_products):
    available_pids = []
    output_file = 'Products.csv'
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        print('Products...', end=' ', flush=True)

        for pid in range(num_products):
            if pid % 100 == 0:
                print(f'{pid}', end=' ', flush=True)
            
            name = fake.sentence(nb_words=4).rstrip('.')
            price = round(fake.random_int(min=1, max=500) + fake.random.random(), 2)
            available_bool = fake.random_element(elements=(True, False))
            available_str = 'TRUE' if available_bool else 'FALSE'
            image_link = f'https://picsum.photos/seed/{pid}/200/200'  # placeholder image link
            
            if available_bool:
                available_pids.append(pid)
            
            # Write all 5 columns: id, name, price, available, image_link
            writer.writerow([pid, name, price, available_str, image_link])
        
        print(f'{num_products} generated; {len(available_pids)} available')

    return available_pids



def gen_purchases(num_purchases, available_pids):
    with open('Purchases.csv', 'w') as f:
        writer = get_csv_writer(f)
        print('Purchases...', end=' ', flush=True)
        for id in range(num_purchases):
            if id % 100 == 0:
                print(f'{id}', end=' ', flush=True)
            uid = fake.random_int(min=0, max=num_users-1)
            pid = fake.random_element(elements=available_pids)
            time_purchased = fake.date_time()
            writer.writerow([id, uid, pid, time_purchased])
        print(f'{num_purchases} generated')
    return

def gen_cart(num_entries, available_pids, num_users):
    with open('Cart.csv', 'w') as f:
        writer = get_csv_writer(f)
        print('Cart...', end=' ', flush=True)
        for cid in range(num_entries):
            if cid % 100 == 0:
                print(f'{cid}', end=' ', flush=True)
            uid = fake.random_int(min=0, max=num_users - 1)
            pid = fake.random_element(elements=available_pids)
            quantity = fake.random_int(min=1, max=5)
            date_added = fake.date_time_this_year()
            writer.writerow([cid, uid, pid, quantity, date_added])
        print(f'{num_entries} generated')
    return


#gen_users(num_users)
#available_pids = gen_products(num_products)
#gen_purchases(num_purchases, available_pids)

available_pids = list(range(num_products))  # make a simple list of product IDs
gen_cart(num_entries=1200, available_pids=available_pids, num_users=num_users)

def gen_product_sellers(num_sellers, available_pids, max_listings_per_seller):
    with open('ProductSeller.csv', 'w', newline='') as f:
        writer = csv.writer(f)  # use default csv.writer, no extra dialect
        for seller_id in range(num_sellers):
            num_listings = fake.random_int(min=5, max=max_listings_per_seller)
            listed_products = fake.random_elements(elements=available_pids, length=num_listings, unique=True)
            for product_id in listed_products:
                price = round(fake.random_int(min=5, max=500) + fake.random.random(), 2)
                quantity = fake.random_int(min=1, max=100)
                is_active = 'TRUE' if fake.random_element(elements=(True, False)) else 'FALSE'
                writer.writerow([seller_id, product_id, price, quantity, is_active])




gen_users(num_users)
available_pids = gen_products(num_products)
gen_purchases(num_purchases, available_pids)
gen_product_sellers(num_sellers=100, available_pids=available_pids, max_listings_per_seller=30)

