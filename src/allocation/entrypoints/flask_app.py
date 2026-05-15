from datetime import datetime
from typing import TYPE_CHECKING, cast

from flask import Flask, Response, jsonify, request

from allocation.bootstrap import bootstrap
from allocation.domain.commands import Allocate, CreateBatch
from allocation.service_layer.handlers import InvalidSkuError
from allocation.views import allocations
from src.allocation.helpers.strenums import ColumnName

if TYPE_CHECKING:
    from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork

app = Flask(__name__)
bus = bootstrap()


@app.route("/add_batch", methods=["POST"])
def add_batch() -> tuple[Response, int]:
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    cmd = CreateBatch(
        request.json[ColumnName.REF],
        request.json[ColumnName.SKU],
        request.json[ColumnName.QTY],
        eta,
    )
    bus.handle(cmd)

    return jsonify({"status": "OK"}), 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint() -> tuple[Response, int]:
    try:
        cmd = Allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
        )
        bus.handle(cmd)

    except InvalidSkuError as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"status": "OK"}), 202


@app.route("/allocations/<orderid>", methods=["GET"])
def allocations_view_endpoint(orderid: str) -> tuple[Response, int]:
    result = allocations(
        orderid,
        cast("SqlAlchemyUnitOfWork", bus.uow),
    )

    if not result:
        return jsonify({"message": "not found"}), 404

    return jsonify(result), 200
