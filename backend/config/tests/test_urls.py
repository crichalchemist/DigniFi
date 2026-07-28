"""Tests for URL routing, especially the SPA catch-all boundary.

The catch-all previously matched r".*", so every unmatched path returned the React
shell with a 200 — including /health (no trailing slash). Uptime checks and deploy
verification read that as healthy while the backend was never consulted. These tests
pin the boundary: backend-owned prefixes must not be swallowed, and React deep-links
must still be.

Note: templates/frontend/index.html is produced by the Docker frontend build and does
not exist here, so SPA expectations are asserted through resolve() rather than by
rendering.
"""

import pytest
from django.test import Client
from django.urls import Resolver404, resolve
from django.views.generic import TemplateView

from config.urls import BACKEND_ROUTE_PREFIXES, SPA_CATCHALL_PATTERN, urlpatterns


def _resolves_to_spa(path: str) -> bool:
    """True when path is served by the SPA catch-all TemplateView."""
    try:
        match = resolve(path)
    except Resolver404:
        return False
    return getattr(match.func, "view_class", None) is TemplateView


@pytest.mark.django_db
class TestBackendPathsAreNotSwallowedBySpa:
    """A probe aimed at the backend must never get a 200 HTML shell instead."""

    def setup_method(self):
        self.client = Client()

    def test_bare_health_redirects_to_canonical_health_url(self):
        """/health must not silently render the SPA.

        This is the exact failure that made a deploy check report healthy while
        never touching Django: the old catch-all resolved /health, so APPEND_SLASH
        never fired. Uses the real client because RequestFactory skips middleware.
        """
        response = self.client.get("/health")
        assert response.status_code == 301
        assert response["Location"] == "/health/"

    def test_following_the_redirect_reaches_the_real_health_view(self):
        response = self.client.get("/health", follow=True)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        assert response.json()["database"] == "ok"

    def test_unknown_api_path_returns_404_not_the_spa_shell(self):
        response = self.client.get("/api/no-such-endpoint/")
        assert response.status_code == 404

    def test_missing_static_asset_is_not_masked_by_the_spa(self):
        """A missing JS bundle must fail loudly, not return HTML with a 200."""
        assert not _resolves_to_spa("/static/frontend/assets/does-not-exist.js")


class TestSpaRoutingIsPreserved:
    """Narrowing the catch-all must not break client-side routing."""

    @pytest.mark.parametrize(
        "route",
        ["/", "/login", "/register", "/terms", "/intake", "/forms", "/documents", "/fee-waiver"],
    )
    def test_react_deep_links_still_serve_the_spa(self, route):
        assert _resolves_to_spa(route)

    def test_unknown_non_backend_path_still_serves_the_spa(self):
        """React renders its own 404 page, so unknown paths stay with the SPA."""
        assert _resolves_to_spa("/some-page-that-does-not-exist")


class TestCatchAllStaysInSyncWithBackendRoutes:
    def test_every_registered_backend_route_is_excluded_from_the_spa(self):
        """Adding a backend route without excluding it would silently reintroduce
        the 200-HTML bug for that prefix, so fail here instead."""
        registered = {
            str(pattern.pattern).split("/")[0]
            for pattern in urlpatterns
            if str(pattern.pattern) != SPA_CATCHALL_PATTERN
        }
        assert registered <= set(BACKEND_ROUTE_PREFIXES), (
            f"backend route(s) {registered - set(BACKEND_ROUTE_PREFIXES)} are not in "
            "BACKEND_ROUTE_PREFIXES and would be swallowed by the SPA catch-all"
        )

    @pytest.mark.parametrize("prefix", BACKEND_ROUTE_PREFIXES)
    def test_each_reserved_prefix_is_excluded_bare_and_nested(self, prefix):
        assert not _resolves_to_spa(f"/{prefix}")
        assert not _resolves_to_spa(f"/{prefix}/anything")

    def test_prefix_exclusion_matches_whole_segments_only(self):
        """'health' is reserved but '/healthy-living' is an ordinary SPA route."""
        assert _resolves_to_spa("/healthy-living")
        assert _resolves_to_spa("/apiary")
