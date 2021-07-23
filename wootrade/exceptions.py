# coding=utf-8
import json


class WootradeAPIException(Exception):
    def __init__(self, resp_json, status_code):
        self.message = resp_json["message"]
        self.code = status_code
        self.api_code = resp_json["code"]

    def __str__(self):
        return f"APIError(code={self.api_code}): {self.message}"


class WootradeValueError:
    def __init__(self, response) -> None:
        self.response = response

    def __str__(self):
        return f"Invalid Response: {self.response.text}"
