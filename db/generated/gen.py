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
    with open('Products.csv', 'w') as f:
        writer = get_csv_writer(f)
        print('Products...', end=' ', flush=True)
        for pid in range(num_products):
            if pid % 100 == 0:
                print(f'{pid}', end=' ', flush=True)
            name = fake.sentence(nb_words=4)[:-1]
            price = f'{str(fake.random_int(max=500))}.{fake.random_int(max=99):02}'
            available = fake.random_element(elements=('true', 'false'))
            if available == 'true':
                available_pids.append(pid)
            writer.writerow([pid, name, price, available])
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


def gen_product_sellers(num_sellers=50, num_products=2000, max_listings_per_seller=50):
    with open('ProductSeller.csv', 'w', newline='') as f:
        writer = get_csv_writer(f)
        print('ProductSeller...', end=' ', flush=True)

        listing_id = 0
        for seller_id in range(num_sellers):
            num_listings = fake.random_int(min=5, max=max_listings_per_seller)
            listed_products = fake.random_elements(elements=list(range(num_products)),
                                                  length=num_listings, unique=True)
            for product_id in listed_products:
                price = f'{fake.random_int(min=5, max=500)}.{fake.random_int(max=99):02}'
                quantity = fake.random_int(min=1, max=100)
                is_active = fake.random_element(elements=('true', 'false'))
                writer.writerow([seller_id, product_id, price, quantity, is_active])
                listing_id += 1

            if seller_id % 5 == 0:
                print(f'{seller_id}', end=' ', flush=True)
        print(f'{num_sellers} sellers generated; {listing_id} listings total')


gen_users(num_users)
available_pids = gen_products(num_products)
gen_purchases(num_purchases, available_pids)
gen_product_sellers(num_sellers=100, num_products=num_products, max_listings_per_seller=30)
