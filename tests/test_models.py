# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_a_product(self):
        """It should Read a product by its ID."""
        product = ProductFactory()
        product.create()
        product_id = product.id
        expected = product.serialize()
        db.session.remove()

        retrieved = Product.find(product_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, product_id)
        self.assertEqual(retrieved.name, expected["name"])
        self.assertEqual(retrieved.description, expected["description"])
        self.assertEqual(retrieved.price, Decimal(expected["price"]))
        self.assertEqual(retrieved.available, expected["available"])
        self.assertEqual(retrieved.category.name, expected["category"])
        self.assertIsNone(Product.find(product_id + 1))

    def test_update_a_product(self):
        """It should persist changes to an existing product."""
        product = ProductFactory(name="Desk", description="Fixed height desk", available=False)
        product.create()
        product_id = product.id
        product.name = "Standing Desk"
        product.description = "Height-adjustable desk"
        product.available = True
        product.update()
        db.session.remove()

        updated = Product.find(product_id)
        self.assertEqual(updated.id, product_id)
        self.assertEqual(updated.name, "Standing Desk")
        self.assertEqual(updated.description, "Height-adjustable desk")
        self.assertTrue(updated.available)
        self.assertEqual(len(Product.all()), 1)

    def test_delete_a_product(self):
        """It should Delete a product from the database."""
        product = ProductFactory()
        product.create()
        product_id = product.id
        self.assertEqual(len(Product.all()), 1)
        product.delete()
        db.session.remove()

        self.assertIsNone(Product.find(product_id))
        self.assertEqual(len(Product.all()), 0)
        self.assertEqual(Product.all(), [])

    def test_list_all_products(self):
        """It should return all saved products."""
        self.assertEqual(Product.all(), [])
        products = ProductFactory.create_batch(3)
        for product in products:
            product.create()

        saved_products = Product.all()
        self.assertEqual(len(saved_products), 3)
        self.assertCountEqual([p.id for p in saved_products], [p.id for p in products])

    def test_find_by_name(self):
        """It should return only products whose name matches."""
        products = [ProductFactory(name=name) for name in ("Hat", "Shoes", "Hat")]
        for product in products:
            product.create()

        name = "Hat"
        expected = [product for product in products if product.name == name]
        matches = Product.find_by_name(name).all()
        self.assertEqual(len(matches), len(expected))
        self.assertCountEqual([p.id for p in matches], [p.id for p in expected])
        for product in matches:
            self.assertEqual(product.name, name)

    def test_find_by_category(self):
        """It should return only products in the requested category."""
        categories = (Category.TOOLS, Category.FOOD, Category.TOOLS)
        products = [ProductFactory(category=category) for category in categories]
        for product in products:
            product.create()

        category = Category.TOOLS
        expected = [product for product in products if product.category == category]
        matches = Product.find_by_category(category).all()
        self.assertEqual(len(matches), len(expected))
        self.assertCountEqual([p.id for p in matches], [p.id for p in expected])
        for product in matches:
            self.assertEqual(product.category, category)

    def test_find_by_availability(self):
        """It should return products for both availability values."""
        in_stock = ProductFactory(available=True)
        out_of_stock = ProductFactory(available=False)
        in_stock.create()
        out_of_stock.create()

        for available, expected in [(True, in_stock), (False, out_of_stock)]:
            with self.subTest(available=available):
                matches = Product.find_by_availability(available).all()
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].id, expected.id)
                for product in matches:
                    self.assertEqual(product.available, available)
