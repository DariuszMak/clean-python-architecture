from datetime import datetime
from typing import TYPE_CHECKING, cast

from flask import Flask, Response, jsonify, request

from src.bootstrap import bootstrap
from src.domain.commands import Allocate, CreateBatch
from src.service_layer.handlers import InvalidStockKeepingUnitError
from src.views import allocations

if TYPE_CHECKING:
    from src.service_layer.unit_of_work import SqlAlchemyUnitOfWork

app = Flask(__name__)
bus = bootstrap()


@app.route("/add_batch", methods=["POST"])
def add_batch() -> tuple[Response, int]:
    estimated_time_of_arrival = request.json["estimated_time_of_arrival"]
    if estimated_time_of_arrival is not None:
        estimated_time_of_arrival = datetime.fromisoformat(estimated_time_of_arrival).date()

    cmd = CreateBatch(
        request.json["reference"],
        request.json["stock_keeping_unit"],
        request.json["quantity"],
        estimated_time_of_arrival,
    )
    bus.handle(cmd)

    return jsonify({"status": "OK"}), 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint() -> tuple[Response, int]:
    try:
        cmd = Allocate(
            request.json["order_id"],
            request.json["stock_keeping_unit"],
            request.json["quantity"],
        )
        bus.handle(cmd)

    except InvalidStockKeepingUnitError as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"status": "OK"}), 202


@app.route("/allocations/<order_id>", methods=["GET"])
def allocations_view_endpoint(order_id: str) -> tuple[Response, int]:
    result = allocations(
        order_id,
        cast("SqlAlchemyUnitOfWork", bus.unit_of_work),
    )

    if not result:
        return jsonify({"message": "not found"}), 404

    return jsonify(result), 200
