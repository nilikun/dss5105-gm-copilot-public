"""Shared fixtures. Expected values come from pandas over the raw CSVs — an independent path from the tools' SQL."""

import pandas as pd
import pytest

from app.clock import SimClock
from app.config import DATA_DIR, DATASET_TODAY
from app.db.database import connect
from app.tools.base import ToolContext

TODAY = pd.Timestamp(DATASET_TODAY)


@pytest.fixture(scope="session")
def db():
    return connect()


@pytest.fixture
def ctx(db):
    return ToolContext(db=db, clock=SimClock.at(DATASET_TODAY))


@pytest.fixture(scope="session")
def orders_df():
    return pd.read_csv(DATA_DIR / "orders.csv",
                       parse_dates=["order_date", "due_date", "last_activity_date", "completed_date"])


@pytest.fixture(scope="session")
def log_df():
    return pd.read_csv(DATA_DIR / "production_log.csv", parse_dates=["date"])
