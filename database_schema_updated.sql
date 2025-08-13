-- =================================
-- DermaCare Database Schema (Updated)
-- 14개 테이블 구조
-- =================================

-- 문자셋 설정 (한글 COMMENT 지원)
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;
SET character_set_connection = utf8mb4;
SET character_set_database = utf8mb4;
SET character_set_results = utf8mb4;
SET character_set_server = utf8mb4;

-- 기존 테이블 삭제 (의존성 순서 고려)
DROP TABLE IF EXISTS Product_Event;
DROP TABLE IF EXISTS Product_Standard;
DROP TABLE IF EXISTS Membership;
DROP TABLE IF EXISTS Info_Event;
DROP TABLE IF EXISTS Info_Membership;
DROP TABLE IF EXISTS Info_Standard;
DROP TABLE IF EXISTS Procedure_Sequence;
DROP TABLE IF EXISTS Procedure_Custom;
DROP TABLE IF EXISTS Procedure_Bundle;
DROP TABLE IF EXISTS Procedure_Class;
DROP TABLE IF EXISTS Procedure_Element;
DROP TABLE IF EXISTS Consumables;
DROP TABLE IF EXISTS Global;
DROP TABLE IF EXISTS Enum;

-- 1. Consumables 테이블 (소모품)
CREATE TABLE Consumables (
    ID INT PRIMARY KEY COMMENT '소모품 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Name VARCHAR(255) COMMENT '소모품 이름',
    Description TEXT NULL COMMENT '소모품 상세 설명',
    Unit_Type VARCHAR(50) COMMENT '단위 타입 (cc, EA, 개 등)',
    I_Value INT COMMENT '정수값',
    F_Value FLOAT COMMENT '실수값',
    Price INT COMMENT '구매가격',
    Unit_Price INT COMMENT '단위별 원가'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='소모품 정보 테이블';

-- 2. Enum 테이블 (커스텀 자료형)
CREATE TABLE Enum (
    enum_type VARCHAR(50) COMMENT '열거형 타입명',
    id INT COMMENT '열거형 ID',
    name VARCHAR(255) COMMENT '열거형 이름',
    PRIMARY KEY (enum_type, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='커스텀 열거형 정의 테이블';

-- 3. Global 테이블 (전역 설정)
CREATE TABLE Global (
    ID INT PRIMARY KEY COMMENT '설정 고유 ID',
    Doc_Price_Minute INT COMMENT '의사 인건비 (분당)',
    Aesthetician_Price_Minute INT COMMENT '관리사 인건비 (분당)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='전역 설정 테이블';

-- 4. Info_Event 테이블 (이벤트 정보)
CREATE TABLE Info_Event (
    ID INT PRIMARY KEY COMMENT '이벤트 정보 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Event_ID INT COMMENT '이벤트 ID',
    Event_Name VARCHAR(255) COMMENT '이벤트 이름',
    Event_Description TEXT COMMENT '이벤트 상세 설명',
    Precautions TEXT COMMENT '주의사항'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='이벤트 정보 테이블';

-- 5. Info_Membership 테이블 (멤버십 정보) - NEW
CREATE TABLE Info_Membership (
    ID INT PRIMARY KEY COMMENT '멤버십 정보 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Membership_ID INT COMMENT '멤버십 ID',
    Membership_Name VARCHAR(255) COMMENT '멤버십 이름',
    Membership_Description TEXT COMMENT '멤버십 상세 설명',
    Precautions TEXT COMMENT '주의사항'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='멤버십 정보 테이블';

-- 6. Info_Standard 테이블 (표준 정보)
CREATE TABLE Info_Standard (
    ID INT PRIMARY KEY COMMENT '표준 정보 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Product_Standard_ID INT COMMENT '표준 상품 ID',
    Product_Standard_Name VARCHAR(255) COMMENT '표준 상품 이름',
    Product_Standard_Description TEXT COMMENT '표준 상품 상세 설명',
    Precautions TEXT COMMENT '주의사항'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='표준 상품 정보 테이블';

-- 7. Membership 테이블 (멤버십 상품)
CREATE TABLE Membership (
    ID INT PRIMARY KEY COMMENT '멤버십 상품 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Membership_Info_ID INT COMMENT '멤버십 정보 ID',
    Payment_Amount INT COMMENT '결제 금액',
    Bonus_Point INT COMMENT '보너스 포인트',
    Credit INT COMMENT '최종 적립금',
    Discount_Rate FLOAT COMMENT '적용 할인율',
    Package_Type VARCHAR(50) COMMENT '패키지 타입 (단일시술, 번들, 커스텀 등)',
    Element_ID INT COMMENT '단일 시술 ID',
    Bundle_ID INT COMMENT '번들 시술 ID',
    Custom_ID INT COMMENT '커스텀 시술 ID',
    Sequence_ID INT COMMENT '시퀀스 시술 ID',
    Validity_Period INT COMMENT '유효기간 (일)',
    Release_Start_Date VARCHAR(20) COMMENT '판매 시작일',
    Release_End_Date VARCHAR(20) COMMENT '판매 종료일'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='멤버십 상품 테이블';

-- 8. Procedure_Bundle 테이블 (시술 번들)
CREATE TABLE Procedure_Bundle (
    GroupID INT COMMENT '그룹 ID',
    ID INT COMMENT '번들 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Name VARCHAR(255) NULL COMMENT '번들 이름',
    Description TEXT NULL COMMENT '번들 설명',
    Element_ID INT COMMENT '단일 시술 ID',
    Element_Cost INT COMMENT '시술 원가',
    Price_Ratio FLOAT COMMENT '가격 비율',
    PRIMARY KEY (GroupID, ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='시술 번들 테이블';

-- 9. Procedure_Class 테이블 (시술 분류)
CREATE TABLE Procedure_Class (
    GroupID INT COMMENT '그룹 ID',
    ID INT COMMENT '분류 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Class_Major VARCHAR(50) COMMENT '시술 대분류 (레이저, 초음파 등)',
    Class_Sub VARCHAR(50) COMMENT '시술 중분류 (리팟, 젠틀맥스 등)',
    Class_Detail VARCHAR(50) COMMENT '시술 상세분류 (안면 제모, 바디 제모 등)',
    Class_Type VARCHAR(50) COMMENT '시술 속성 (제모, 쁘띠 등)',
    PRIMARY KEY (GroupID, ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='시술 분류 테이블';

-- 10. Procedure_Custom 테이블 (커스텀 시술) - NEW
CREATE TABLE Procedure_Custom (
    GroupID INT COMMENT '그룹 ID',
    ID INT COMMENT '커스텀 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Name VARCHAR(255) COMMENT '커스텀 시술 이름',
    Description TEXT COMMENT '커스텀 시술 설명',
    Element_ID INT COMMENT '단일 시술 ID',
    Custom_Count INT COMMENT '시술 횟수',
    Element_Limit INT COMMENT '개별 횟수 제한',
    Element_Cost INT COMMENT '시술 원가',
    Price_Ratio FLOAT COMMENT '가격 비율',
    PRIMARY KEY (GroupID, ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='커스텀 시술 테이블';

-- 11. Procedure_Element 테이블 (시술 요소)
CREATE TABLE Procedure_Element (
    ID INT PRIMARY KEY COMMENT '시술 요소 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Class_Major VARCHAR(50) COMMENT '시술 대분류',
    Class_Sub VARCHAR(50) COMMENT '시술 중분류',
    Class_Detail VARCHAR(50) COMMENT '시술 상세분류',
    Class_Type VARCHAR(50) COMMENT '시술 속성',
    Name VARCHAR(255) COMMENT '단일 시술 이름',
    description TEXT COMMENT '단일 시술 설명',
    Position_Type VARCHAR(50) COMMENT '시술자 타입',
    Cost_Time FLOAT COMMENT '소요 시간 (분)',
    Plan_State BOOLEAN COMMENT '플랜 여부',
    Plan_Count INT COMMENT '플랜 횟수',
    Consum_1_ID INT COMMENT '소모품 1 ID',
    Consum_1_Count INT COMMENT '소모품 1 개수',
    Procedure_Level VARCHAR(50) COMMENT '시술 난이도 (매우쉬움, 쉬움, 보통, 어려움, 매우어려움)',
    Procedure_Cost INT COMMENT '시술 원가',
    Price INT COMMENT '시술 가격'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='시술 요소 테이블';

-- 12. Procedure_Sequence 테이블 (시술 순서)
CREATE TABLE Procedure_Sequence (
    GroupID INT COMMENT '그룹 ID',
    ID INT COMMENT '시퀀스 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Step_Num INT COMMENT '순서 번호',
    Element_ID INT COMMENT '단일 시술 ID',
    Bundle_ID INT COMMENT '번들 시술 ID',
    Custom_ID INT COMMENT '커스텀 시술 ID',
    Procedure_Cost INT COMMENT '시술 원가',
    Price_Ratio FLOAT COMMENT '가격 비율',
    PRIMARY KEY (GroupID, ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='시술 순서 테이블';

-- 13. Product_Event 테이블 (이벤트 상품)
CREATE TABLE Product_Event (
    ID INT PRIMARY KEY COMMENT '이벤트 상품 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Package_Type VARCHAR(50) COMMENT '패키지 타입',
    Element_ID INT COMMENT '단일 시술 ID',
    Bundle_ID INT COMMENT '번들 시술 ID',
    Custom_ID INT COMMENT '커스텀 시술 ID',
    Sequence_ID INT COMMENT '시퀀스 시술 ID',
    Event_Info_ID INT COMMENT '이벤트 정보 ID',
    Procedure_Cost INT COMMENT '시술 원가',
    Sell_Price INT COMMENT '실제 판매가',
    Discount_Rate FLOAT COMMENT '할인율',
    Original_Price INT COMMENT '정상가',
    Margin INT COMMENT '마진값',
    Margin_Rate FLOAT COMMENT '마진율',
    Event_Start_Date VARCHAR(20) COMMENT '이벤트 시작일',
    Event_End_Date VARCHAR(20) COMMENT '이벤트 종료일',
    Validity_Period INT COMMENT '유효기간 (일)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='이벤트 상품 테이블';

-- 14. Product_Standard 테이블 (표준 상품)
CREATE TABLE Product_Standard (
    ID INT PRIMARY KEY COMMENT '표준 상품 고유 ID',
    `Release` INT COMMENT '활성/비활성 여부',
    Package_Type VARCHAR(50) COMMENT '패키지 타입',
    Element_ID INT COMMENT '단일 시술 ID',
    Bundle_ID INT COMMENT '번들 시술 ID',
    Custom_ID INT COMMENT '커스텀 시술 ID',
    Sequence_ID INT COMMENT '시퀀스 시술 ID',
    Standard_Info_ID INT COMMENT '표준 정보 ID',
    Procedure_Cost INT COMMENT '시술 원가',
    Sell_Price INT COMMENT '실제 판매가',
    Discount_Rate FLOAT COMMENT '할인율',
    Original_Price INT COMMENT '정상가',
    Margin INT COMMENT '마진값',
    Margin_Rate FLOAT COMMENT '마진율',
    Standard_Start_Date VARCHAR(20) COMMENT '상품 노출 시작일',
    Standard_End_Date VARCHAR(20) COMMENT '상품 노출 종료일',
    Validity_Period INT COMMENT '유효기간 (일)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='표준 상품 테이블';

-- =================================
-- 테이블 생성 완료
-- 총 14개 테이블
-- =================================
