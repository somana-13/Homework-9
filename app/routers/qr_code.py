# app/routers/qr_code.py

from fastapi import APIRouter, HTTPException, Depends, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from typing import List
import os, logging

from app.schema import QRCodeRequest, QRCodeResponse
from app.services.qr_service import generate_qr_code, list_qr_codes, delete_qr_code
from app.utils.common import (
    decode_filename_to_url,
    encode_url_to_filename,
    generate_links,
)
from app.config import (
    QR_DIRECTORY,
    SERVER_BASE_URL,
    FILL_COLOR,
    BACK_COLOR,
    SERVER_DOWNLOAD_FOLDER,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(
    prefix="/qr-codes",
    tags=["QR Codes"],
    dependencies=[Depends(oauth2_scheme)],
)

@router.post(
    "/",
    response_model=QRCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_qr_code(request: QRCodeRequest):
    logging.info(f"Creating QR code for URL: {request.url}")
    encoded = encode_url_to_filename(request.url)
    qr_filename = f"{encoded}.png"
    qr_path = QR_DIRECTORY / qr_filename
    download_url = f"{SERVER_BASE_URL}/{SERVER_DOWNLOAD_FOLDER}/{qr_filename}"
    links = generate_links("create", qr_filename, SERVER_BASE_URL, download_url)

    if qr_path.exists():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": "QR code already exists.", "links": links},
        )

    generate_qr_code(request.url, qr_path, FILL_COLOR, BACK_COLOR, request.size)
    return QRCodeResponse(
        message="QR code created successfully.",
        qr_code_url=download_url,
        links=links,
    )


@router.get(
    "/",
    response_model=List[QRCodeResponse],
)
async def list_qr_codes_endpoint():
    logging.info("Listing all QR codes.")
    qr_files = list_qr_codes(QR_DIRECTORY)
    return [
        QRCodeResponse(
            message="QR code available",
            qr_code_url=decode_filename_to_url(fname[:-4]),
            links=generate_links(
                "list",
                fname,
                SERVER_BASE_URL,
                f"{SERVER_BASE_URL}/{SERVER_DOWNLOAD_FOLDER}/{fname}",
            ),
        )
        for fname in qr_files
    ]


@router.get(
    "/{qr_filename}",
    response_class=FileResponse,
    responses={200: {"content": {"image/png": {}}}, 404: {"description": "Not found"}},
)
def retrieve_qr_code(qr_filename: str):
    file_path = os.path.join(QR_DIRECTORY, qr_filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="QR code not found")
    return FileResponse(file_path, media_type="image/png")


@router.delete(
    "/{qr_filename}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_qr_code_endpoint(qr_filename: str):
    logging.info(f"Deleting QR code: {qr_filename}")
    qr_path = QR_DIRECTORY / qr_filename
    if not qr_path.is_file():
        raise HTTPException(status_code=404, detail="QR code not found")
    delete_qr_code(qr_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
