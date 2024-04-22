import pytest
from woox import Client
from woox import ThreadedWebsocketManager
import os

API = os.getenv("API")
SECRET = os.getenv("SECRET")
APPLICATION_ID = os.getenv("APPLICATION_ID")


def test_create_TWM():
    wsm = ThreadedWebsocketManager(API, SECRET, APPLICATION_ID, False)
