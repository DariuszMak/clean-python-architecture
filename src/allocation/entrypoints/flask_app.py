from datetime import datetime
from typing import TYPE_CHECKING, cast

from flask import Flask, Response, jsonify, request

from allocation import bootstrap, views
from allocation.domain import commands
from allocation.service_layer.handlers import InvalidSkuError

if TYPE_CHECKING:
    from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork

app = Flask(__name__)
bus = bootstrap.bootstrap()


@app.route("/add_batch", methods=["POST"])
def add_batch() -> tuple[Response, int]:
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

    return jsonify({"status": "OK"}), 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint() -> tuple[Response, int]:
    try:
        cmd = commands.Allocate(
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
    result = views.allocations(
        orderid,
        cast("SqlAlchemyUnitOfWork", bus.uow),
    )

    if not result:
        return jsonify({"message": "not found"}), 404

    return jsonify(result), 200
