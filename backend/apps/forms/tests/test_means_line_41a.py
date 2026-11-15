"""Line 41a is 106Sum line 3b; the means test's own sum of it never drifts from the form's."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.eligibility.means_inputs import read_inputs
from apps.forms.services.derivations import DERIVATIONS
from apps.intake.models import IntakeSession


@pytest.mark.slow
@pytest.mark.django_db
@pytest.mark.parametrize("persona", ["maria", "james", "priya", "deshawn", "sarah", "andres"])
def test_line_41a_is_what_106sum_line_3b_prints(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona=persona, verbosity=0)
    session = IntakeSession.objects.filter(user__username=f"demo_{persona}").latest("id")
    assert read_inputs(session).line_41a == Decimal(
        DERIVATIONS["total_nonpriority_unsecured"](session)
    )
