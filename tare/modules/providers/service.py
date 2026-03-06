"""Providers. Everybody reads them; only the bureau registers one."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Provider
from tare.modules.providers.rules import KINDS, account_is_sound, of_kind, sort_by_code
from tare.modules.providers.schemas import (
    ChangeAccount, ListProviders, RegisterProvider,
)


class ProvidersService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def list(self, operator: Operator, query: ListProviders) -> dict:
        rows = sort_by_code(self.store.providers.all())
        if query.kind:
            rows = of_kind(rows, query.kind)
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, provider_id: str) -> Provider:
        row = self.store.providers.find(provider_id)
        if not row:
            raise not_found("provider", provider_id)
        return row

    def register(self, operator: Operator, dto: RegisterProvider) -> Provider:
        assert_bureau(operator, "register a provider")
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not a kind of provider this service holds")
        if not account_is_sound(dto.account):
            raise refuse(f"{dto.account} does not read as an account")
        if self.store.providers.first(lambda row: row.code == dto.code):
            raise conflict(f"provider {dto.code} is already registered")
        return self.store.providers.insert(Provider(
            id="", code=dto.code, name=dto.name, kind=dto.kind, account=dto.account))

    def change_account(
        self, operator: Operator, provider_id: str, dto: ChangeAccount,
    ) -> Provider:
        assert_bureau(operator, "change a provider's account")
        row = self.get(operator, provider_id)
        if not account_is_sound(dto.account):
            raise refuse(f"{dto.account} does not read as an account")
        return self.store.providers.update(row.id, account=dto.account)
