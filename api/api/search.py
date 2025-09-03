"""
    검색 API
    시술 통합 검색 기능 제공 - Element, Bundle, Custom, Sequence 검색
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, func
from typing import List, Optional

from db.session import get_db
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence

search_router = APIRouter(prefix="/search", tags=["검색"])

"""
    시술 통합 검색 API
    
    하나의 검색어로 Element, Bundle, Custom, Sequence를 통합 검색함.
    시술명, 분류 등 모든 필드에서 검색하여 Product 생성 시 시술 선택에 활용.
"""

@search_router.get("/products")
def search_procedures(
    q: str = Query(..., description="검색어 (시술명, 분류 등 모든 필드에서 검색)"),
    procedure_type: str = Query("all", description="시술 타입 (all/element/bundle/custom/sequence)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(30, ge=1, le=1000, description="페이지 크기"),
    db: Session = Depends(get_db)
):
    try:
        # 파라미터 검증: 시술 타입 확인
        if procedure_type not in ["all", "element", "bundle", "custom", "sequence"]:
            raise HTTPException(
                status_code=400, 
                detail="잘못된 시술 타입입니다. (all/element/bundle/custom/sequence 중 선택)"
            )
        
        # 파라미터 검증: 검색어 확인
        if not q or not q.strip():
            raise HTTPException(
                status_code=400,
                detail="검색어를 입력해주세요."
            )
        
        # 검색어 정리
        search_term = q.strip()
        
        # 시술 타입별 리스트 분리
        all_procedures = []
        
        # Element 검색
        if procedure_type in ["all", "element"]:
            try:
                elements = db.query(ProcedureElement).filter(
                    ProcedureElement.Release == 1,
                    or_(
                        # 시술명 검색
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Name.endswith(search_term),
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        # 분류 검색
                        ProcedureElement.Class_Major.contains(search_term),
                        ProcedureElement.Class_Sub.contains(search_term),
                        ProcedureElement.Class_Detail.contains(search_term),
                        ProcedureElement.Class_Type.contains(search_term),
                        # 설명 검색
                        ProcedureElement.description.contains(search_term),
                        func.lower(ProcedureElement.description).contains(func.lower(search_term))
                    )
                ).all()
                
                for element in elements:
                    all_procedures.append({
                        "type": "element",
                        "id": element.ID,
                        "name": element.Name,
                        "description": element.description,
                        "procedure_cost": element.Procedure_Cost,
                        "category": f"{element.Class_Major} > {element.Class_Sub} > {element.Class_Detail}",
                        "class_type": element.Class_Type,
                        "class_major": element.Class_Major,
                        "class_sub": element.Class_Sub,
                        "class_detail": element.Class_Detail,
                        "position_type": element.Position_Type,
                        "cost_time": element.Cost_Time,
                        "plan_state": element.Plan_State,
                        "plan_count": element.Plan_Count,
                        "consum_1_id": element.Consum_1_ID,
                        "consum_1_count": element.Consum_1_Count,
                        "price": element.Price,
                        "release": element.Release
                    })
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Element 검색 중 오류 발생: {str(e)}"
                )
        
        # Bundle 검색
        if procedure_type in ["all", "bundle"]:
            try:
                bundles = db.query(ProcedureBundle).filter(
                    ProcedureBundle.Release == 1,
                    or_(
                        # 번들명 검색
                        ProcedureBundle.Name.contains(search_term),
                        ProcedureBundle.Name.startswith(search_term),
                        ProcedureBundle.Name.endswith(search_term),
                        func.lower(ProcedureBundle.Name).contains(func.lower(search_term)),
                        # 설명 검색
                        ProcedureBundle.Description.contains(search_term),
                        func.lower(ProcedureBundle.Description).contains(func.lower(search_term))
                    )
                ).all()
                
                for bundle in bundles:
                    # Bundle의 총 비용과 Element 개수 계산
                    bundle_elements = db.query(ProcedureBundle).filter(
                        ProcedureBundle.GroupID == bundle.GroupID,
                        ProcedureBundle.Release == 1
                            ).all()
                            
                    total_cost = sum(b.Element_Cost for b in bundle_elements)
                    element_count = len(bundle_elements)
                    
                    all_procedures.append({
                        "type": "bundle",
                        "id": bundle.GroupID,
                        "name": bundle.Name,
                        "description": bundle.Description,
                        "procedure_cost": total_cost,
                        "category": "번들",
                        "element_count": element_count,
                        "price_ratio": bundle.Price_Ratio,
                        "release": bundle.Release
                    })
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Bundle 검색 중 오류 발생: {str(e)}"
                )
        
        # Custom 검색
        if procedure_type in ["all", "custom"]:
            try:
                customs = db.query(ProcedureCustom).filter(
                    ProcedureCustom.Release == 1,
                    or_(
                        # 커스텀명 검색
                        ProcedureCustom.Name.contains(search_term),
                        ProcedureCustom.Name.startswith(search_term),
                        ProcedureCustom.Name.endswith(search_term),
                        func.lower(ProcedureCustom.Name).contains(func.lower(search_term)),
                        # 설명 검색
                        ProcedureCustom.Description.contains(search_term),
                        func.lower(ProcedureCustom.Description).contains(func.lower(search_term))
                    )
                ).all()
                
                for custom in customs:
                    # Custom의 총 비용과 Element 개수 계산
                    custom_elements = db.query(ProcedureCustom).filter(
                        ProcedureCustom.GroupID == custom.GroupID,
                        ProcedureCustom.Release == 1
                    ).all()
                    
                    total_cost = sum(c.Element_Cost for c in custom_elements)
                    element_count = len(custom_elements)
                    
                    all_procedures.append({
                        "type": "custom",
                        "id": custom.GroupID,
                        "name": custom.Name,
                        "description": custom.Description,
                        "procedure_cost": total_cost,
                        "category": "커스텀",
                        "element_count": element_count,
                        "custom_count": custom.Custom_Count,
                        "element_limit": custom.Element_Limit,
                        "price_ratio": custom.Price_Ratio,
                        "release": custom.Release
                    })
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Custom 검색 중 오류 발생: {str(e)}"
                )
        
        # Sequence 검색
        if procedure_type in ["all", "sequence"]:
            try:
                sequences = db.query(ProcedureSequence).filter(
                    ProcedureSequence.Release == 1
                ).all()
                
                # Sequence는 GroupID별로 그룹화하여 처리
                sequence_groups = {}
                for sequence in sequences:
                    if sequence.GroupID not in sequence_groups:
                        sequence_groups[sequence.GroupID] = {
                            "steps": [],
                            "total_cost": 0
                        }
                    
                    sequence_groups[sequence.GroupID]["steps"].append({
                        "step_num": sequence.Step_Num,
                        "element_id": sequence.Element_ID,
                        "bundle_id": sequence.Bundle_ID,
                        "custom_id": sequence.Custom_ID,
                        "sequence_interval": sequence.Sequence_Interval,
                        "procedure_cost": sequence.Procedure_Cost,
                        "price_ratio": sequence.Price_Ratio
                    })
                    
                    sequence_groups[sequence.GroupID]["total_cost"] += sequence.Procedure_Cost
                
                # Sequence 그룹별로 검색어 매칭 확인
                for group_id, group_data in sequence_groups.items():
                    # Sequence 내 Element, Bundle, Custom 정보 조회하여 검색어 매칭 확인
                    matched = False
                    
                    for step in group_data["steps"]:
                        if step["element_id"]:
                            element = db.query(ProcedureElement).filter(
                                ProcedureElement.ID == step["element_id"],
                                ProcedureElement.Release == 1
                            ).first()
                            
                            if element and (
                                search_term in element.Name or
                                search_term in element.Class_Major or
                                search_term in element.Class_Sub or
                                search_term in element.Class_Detail or
                                search_term in element.Class_Type
                            ):
                                matched = True
                                break
                        
                        elif step["bundle_id"]:
                            bundle = db.query(ProcedureBundle).filter(
                                ProcedureBundle.GroupID == step["bundle_id"],
                                ProcedureBundle.Release == 1
                            ).first()
                            
                            if bundle and search_term in bundle.Name:
                                matched = True
                                break
                        
                        elif step["custom_id"]:
                            custom = db.query(ProcedureCustom).filter(
                                ProcedureCustom.GroupID == step["custom_id"],
                                ProcedureCustom.Release == 1
                            ).first()
                            
                            if custom and search_term in custom.Name:
                                matched = True
                                break
                    
                    if matched:
                        all_procedures.append({
                            "type": "sequence",
                            "id": group_id,
                            "name": f"시퀀스 {group_id}",
                            "description": f"총 {len(group_data['steps'])}개 Step으로 구성된 시퀀스",
                            "procedure_cost": group_data["total_cost"],
                            "category": "시퀀스",
                            "step_count": len(group_data["steps"]),
                            "steps": group_data["steps"],
                            "release": 1
                        })
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Sequence 검색 중 오류 발생: {str(e)}"
                )
        
        # 페이지네이션 적용
        try:
            total_count = len(all_procedures)
            total_pages = (total_count + page_size - 1) // page_size
            
            # 페이지 번호 검증
            if page > total_pages and total_pages > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"요청된 페이지({page})가 총 페이지 수({total_pages})를 초과합니다."
                )
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_procedures = all_procedures[start_index:end_index]
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"페이지네이션 처리 중 오류 발생: {str(e)}"
            )
        
        # 응답 데이터 구성
        try:
            response_data = {
                "status": "success",
                "message": f"시술 검색 완료 (총 {total_count}개)",
                "data": paginated_procedures,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages
                },
                "search_info": {
                    "query": search_term,
                    "procedure_type": procedure_type
                }
            }
            
            return response_data
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"응답 데이터 구성 중 오류 발생: {str(e)}"
            )
        
    except HTTPException:
        raise
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 파라미터 값: {str(e)}"
        )
    
    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 데이터 타입: {str(e)}"
        )
    
    except Exception as e:
        # 로그 기록 (실제 운영환경에서는 로깅 라이브러리 사용)
        print(f"시술 검색 API 오류: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"시술 검색 중 오류 발생: {str(e)}"
        )
