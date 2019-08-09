from glob import glob
import os

from mlcomp.db.core import Session
from mlcomp.db.models import ReportLayout
from mlcomp.db.providers import ReportLayoutProvider
from mlcomp.utils.misc import now

_session = Session.create_session()


def upgrade(migrate_engine):
    folder = os.path.dirname(__file__)
    provider = ReportLayoutProvider(_session)
    try:
        files = os.path.join(folder, '002', 'report_layout', '*.yml')
        for path in glob(files):
            name = str(os.path.basename(path).split('.')[0])
            text = open(path).read()
            provider.add(
                ReportLayout(name=name, content=text, last_modified=now()),
                commit=False
            )

        provider.commit()
    except Exception:
        provider.rollback()
        raise


def downgrade(migrate_engine):
    provider = ReportLayoutProvider(_session)
    provider.session.query(ReportLayout).delete(synchronize_session=False)
    provider.session.commit()
