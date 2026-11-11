######################################################################
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
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import Category, db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        retrieved = self.client.get(location)
        self.assertEqual(retrieved.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieved.get_json(), new_product)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """It should return a product by ID and 404 for a missing ID."""
        product = self._create_products()[0]
        response = self.client.get(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = product.serialize()
        actual = response.get_json()
        expected["price"] = Decimal(expected["price"])
        actual["price"] = Decimal(actual["price"])
        self.assertEqual(actual, expected)
        missing = self.client.get(f"{BASE_URL}/{product.id + 1}")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        """It should persist the fields sent in a PUT request."""
        product = ProductFactory(name="Desk", description="Fixed height desk")
        created = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        data = created.get_json()
        product_id = data["id"]
        url = f"{BASE_URL}/{product_id}"
        data["name"] = "Standing Desk"
        data["description"] = "Height-adjustable desk"
        data["available"] = False

        response = self.client.put(url, json=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated = response.get_json()
        self.assertEqual(updated["id"], product_id)
        self.assertEqual(updated["name"], "Standing Desk")
        self.assertEqual(updated["description"], "Height-adjustable desk")
        self.assertIs(updated["available"], False)
        self.assertEqual(self.client.get(url).get_json(), updated)

    def test_delete_product(self):
        """It should delete a product and return an empty 204 response."""
        product = self._create_products(2)[0]
        count_before = self.get_product_count()
        url = f"{BASE_URL}/{product.id}"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")
        self.assertEqual(self.get_product_count(), count_before - 1)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_list_all_products(self):
        """It should return the full product collection."""
        products = self._create_products(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [product["id"] for product in response.get_json()],
            [product.id for product in products],
        )

    def test_list_by_name(self):
        """It should filter the collection by an exact name."""
        product = ProductFactory(name="Big Mac")
        product.create()
        ProductFactory(name="Hat").create()
        response = self.client.get(BASE_URL, query_string={"name": "Big Mac"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matches = response.get_json()
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], product.id)
        self.assertEqual(matches[0]["name"], "Big Mac")

    def test_list_by_category(self):
        """It should filter the collection by category."""
        product = ProductFactory(category=Category.TOOLS)
        product.create()
        ProductFactory(category=Category.FOOD).create()
        response = self.client.get(BASE_URL, query_string={"category": "TOOLS"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matches = response.get_json()
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], product.id)
        self.assertEqual(matches[0]["category"], "TOOLS")

    def test_list_by_availability(self):
        """It should distinguish available from unavailable products."""
        in_stock = ProductFactory(available=True)
        out_of_stock = ProductFactory(available=False)
        in_stock.create()
        out_of_stock.create()
        for value, product in [("true", in_stock), ("false", out_of_stock)]:
            with self.subTest(available=value):
                response = self.client.get(BASE_URL, query_string={"available": value})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                matches = response.get_json()
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0]["id"], product.id)
                self.assertIs(matches[0]["available"], value == "true")

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
