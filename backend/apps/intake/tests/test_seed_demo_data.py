"""The demo seed checks for a median table in force before it deletes anything (3a1 spec §3).

Business intent: the demo personas carry the partner demos and the E2E journeys. A reseed
that can't work their means tests out must leave the existing personas as they are and tell
the operator where to find how to load the missing table.
"""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.districts.models import MedianIncome
from apps.users.models import User


@pytest.mark.django_db
def test_a_reseed_with_no_median_table_in_force_keeps_the_demo_personas_and_points_to_the_runbook():
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="james", stdout=StringIO())
    james = User.objects.get(username="demo_james").pk
    MedianIncome.objects.all().delete()
    err = StringIO()

    call_command("seed_demo_data", "--reset", stdout=StringIO(), stderr=err)

    assert User.objects.get(username="demo_james").pk == james
    assert "docs/REFERENCE_TABLES.md" in err.getvalue()
