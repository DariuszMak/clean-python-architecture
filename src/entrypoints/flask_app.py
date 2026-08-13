from datetime import date # noqa
from typing import TYPE_CHECKING, cast

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.bootstrap import bootstrap
from src.domain.commands import Allocate, CreateBatch
from src.service_layer.handlers import InvalidStockKeepingUnitError
from src.views import allocations

if TYPE_CHECKING:

    from src.service_layer.unit_of_work import SqlAlchemyUnitOfWork

app = FastAPI()
bus = bootstrap()


class AddBatchRequest(BaseModel):
    reference: str
    stock_keeping_unit: str
    quantity: int
    estimated_time_of_arrival: date | None = None


class AllocateRequest(BaseModel):
    order_id: str
    stock_keeping_unit: str
    quantity: int


AddBatchRequest.model_rebuild()
AllocateRequest.model_rebuild()


@app.post("/add_batch", status_code=status.HTTP_201_CREATED)
def add_batch(request_data: AddBatchRequest) -> dict[str, str]:
    cmd = CreateBatch(
        request_data.reference,
        request_data.stock_keeping_unit,
        request_data.quantity,
        request_data.estimated_time_of_arrival,
    )
    bus.handle(cmd)

    return {"status": "OK"}


@app.post("/allocate", status_code=status.HTTP_202_ACCEPTED)
def allocate_endpoint(request_data: AllocateRequest) -> JSONResponse:
    try:
        cmd = Allocate(
            request_data.order_id,
            request_data.stock_keeping_unit,
            request_data.quantity,
        )
        bus.handle(cmd)
    except InvalidStockKeepingUnitError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(e)},
        )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"status": "OK"},
    )


@app.get("/allocations/{order_id}")
def allocations_view_endpoint(order_id: str) -> JSONResponse:
    result = allocations(
        order_id,
        cast("SqlAlchemyUnitOfWork", bus.unit_of_work),
    )

    if not result:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "not found"},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result,
    )
