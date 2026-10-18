'''Suite-wide application context.

Every legacy helper generated from the recorded skeleton reaches the database
through ``Model.query``. Flask-SQLAlchemy scopes that session to the current
application context, so calling such a helper from a bare unit test raises
``RuntimeError: Working outside of application context``. Pushing the real
application context here keeps those helpers honest: they run against the same
engine and the same schema the service itself uses.
'''
import pytest


@pytest.fixture(autouse=True)
def legacy_app_context(settings):
    '''Push a real application context for every test in the suite.'''
    from easylpac.app import create_app
    from easylpac.models import db

    application = create_app(settings)
    with application.app_context():
        # Every test starts from an empty schema. The engine points at the
        # throwaway database installed by the root conftest, never var/.
        db.drop_all()
        db.create_all()
        yield application
