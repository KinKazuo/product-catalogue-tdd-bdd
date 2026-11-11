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
Product Steps

Steps file for products.feature

For information on Waiting until elements are present in the HTML see:
    https://selenium-python.readthedocs.io/waits.html
"""
import requests
from behave import given

# HTTP Return Codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204

@given('the following products')
def load_products(context):
    """Reset the test catalogue and load the products from the background table."""
    rest_endpoint = f"{context.base_url}/products"
    response = requests.get(rest_endpoint, timeout=10)
    assert response.status_code == HTTP_200_OK, response.text
    for product in response.json():
        response = requests.delete(f"{rest_endpoint}/{product['id']}", timeout=10)
        assert response.status_code == HTTP_204_NO_CONTENT, response.text

    for row in context.table:
        product = {
            "name": row["name"],
            "description": row["description"],
            "price": row["price"],
            "available": row["available"].lower() == "true",
            "category": row["category"],
        }
        response = requests.post(rest_endpoint, json=product, timeout=10)
        assert response.status_code == HTTP_201_CREATED, response.text
