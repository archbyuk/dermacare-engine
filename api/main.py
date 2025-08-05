from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
import io

from db.session import get_db
from db.models.enum import Enum
from db.models.consumables import Consumables
from db.models.global_config import Global
from db.models.procedure_element import ProcedureElement
from db.models.procedure_bundle import ProcedureBundle
from db.models.procedure_sequence import ProcedureSequence
from db.models.procedure_info import ProcedureInfo
from db.models.procedure_product import ProcedureProduct

app = FastAPI(
    title="DermaCare API",
    description="DermaCare 시술 관리 시스템 API",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "This is DermaCare API server"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "api server is running properly"}

@app.get("/db-test")
def test_database_connection(db: Session = Depends(get_db)):
    """데이터베이스 연결 테스트"""
    try:
        # Enum 테이블에서 첫 번째 레코드 조회
        enum_count = db.query(Enum).count()
        return {
            "status": "success",
            "message": "database connection successful",
            "enum_count": enum_count
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Database connection failed: {str(e)}"
        }

@app.post("/upload-excel")
async def upload_excel_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """엑셀 파일 업로드 및 파싱"""
    
    # 파일 확장자 검증
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="엑셀 파일만 업로드 가능합니다 (.xlsx, .xls)"
        )
    
    try:
        # 파일 내용 읽기
        contents = await file.read()
        
        # pandas로 엑셀 파일 파싱
        df = pd.read_excel(io.BytesIO(contents))
        
        # 기본 정보 반환
        result = {
            "status": "success",
            "message": "엑셀 파일 업로드 및 파싱 완료",
            "file_info": {
                "filename": file.filename,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist()
            },
            "preview": df.head(5).to_dict('records'),  # 첫 5행 미리보기
            "data_types": df.dtypes.astype(str).to_dict()
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 처리 중 오류 발생: {str(e)}"
        )

@app.post("/upload-excel-to-db")
async def upload_excel_to_database(
    file: UploadFile = File(...),
    table_name: str = "enum",
    db: Session = Depends(get_db)
):
    """엑셀 파일을 데이터베이스에 직접 삽입"""
    
    # 파일 확장자 검증
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="엑셀 파일만 업로드 가능합니다 (.xlsx, .xls)"
        )
    
    try:
        # 파일 내용 읽기
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 테이블별 데이터 삽입 로직
        inserted_count = 0
        errors = []
        
        if table_name.lower() == "enum":
            # Enum 테이블에 삽입
            for index, row in df.iterrows():
                try:
                    enum_item = Enum(
                        Type=str(row.get('Type', '')),
                        Code=str(row.get('Code', '')),
                        Name=str(row.get('Name', ''))
                    )
                    db.add(enum_item)
                    inserted_count += 1
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
        
        elif table_name.lower() == "consumables":
            # Consumables 테이블에 삽입
            for index, row in df.iterrows():
                try:
                    consumable = Consumables(
                        Name=str(row.get('Name', '')),
                        Description=str(row.get('Description', '')),
                        Unit_Type=str(row.get('Unit_Type', '')),
                        I_Value=int(row.get('I_Value', 0)) if pd.notna(row.get('I_Value')) else None,
                        F_Value=float(row.get('F_Value', 0)) if pd.notna(row.get('F_Value')) else None,
                        Price=int(row.get('Price', 0)) if pd.notna(row.get('Price')) else None,
                        Unit_Price=int(row.get('Unit_Price', 0)) if pd.notna(row.get('Unit_Price')) else None
                    )
                    db.add(consumable)
                    inserted_count += 1
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 테이블입니다: {table_name}"
            )
        
        # 데이터베이스 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": f"{table_name} 테이블에 데이터 삽입 완료",
            "file_info": {
                "filename": file.filename,
                "total_rows": len(df),
                "inserted_count": inserted_count,
                "error_count": len(errors)
            },
            "errors": errors if errors else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"데이터베이스 삽입 중 오류 발생: {str(e)}"
        )