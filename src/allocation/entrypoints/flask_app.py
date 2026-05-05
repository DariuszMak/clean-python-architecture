from datetime import datetime
from typing import cast

from flask import Flask, jsonify, request, Response

from allocation import bootstrap, views
from allocation.domain import commands
from allocation.service_layer.handlers import InvalidSkuError
from allocation.adapters.unit_of_work import SqlAlchemyUnitOfWork

app = Flask(__name__)
bus = bootstrap.bootstrap()


@app.route("/add_batch", methods=["POST"])
def add_batch() -> tuple[str, int]:
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    cmd = commands.CreateBatch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta,
    )
    bus.handle(cmd)
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint() -> Response | tuple[str, int]:
    try:
        cmd = commands.Allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
        )
        bus.handle(cmd)
    except InvalidSkuError as e:
        return jsonify({"message": str(e)}), 400

    return "OK", 202


@app.route("/allocations/<orderid>", methods=["GET"])
def allocations_view_endpoint(orderid: str) -> Response | tuple[str, int]:
    result = views.allocations(orderid, cast("SqlAlchemyUnitOfWork", bus.uow))
    if not result:
        return "not found", 404
    return jsonify(result), 200