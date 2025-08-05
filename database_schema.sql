-- DermaCare Database Schema
-- 시술 관리 시스템을 위한 데이터베이스 스키마

-- Enum: 공통 코드 테이블 (타입별 Enum 값 저장)
CREATE TABLE Enum (
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '고유 ID',
    `Release` BOOLEAN DEFAULT TRUE COMMENT '비/활성 여부',
    Type VARCHAR(50) NOT NULL COMMENT 'enum 분류 (ex: ProcedureType)',
    Code VARCHAR(100) NOT NULL COMMENT '실제 값',
    Name VARCHAR(255) COMMENT '표시용 이름',
    UNIQUE KEY unique_type_code (Type, Code)
);

-- Consumables: 시술에 사용되는 소모품 정보
CREATE TABLE Consumables (
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '소모품 고유 ID',
    `Release` BOOLEAN DEFAULT TRUE COMMENT '비/활성 여부',
    Name VARCHAR(255) NOT NULL COMMENT '소모품 이름',
    Description TEXT COMMENT '소모품 설명',
    Unit_Type VARCHAR(100) COMMENT '단위 (enum UnitType)',
    I_Value INT COMMENT '정수값',
    F_Value FLOAT COMMENT '실수값',
    Price INT COMMENT '소모품 구매 가격',
    Unit_Price INT COMMENT '단위 기준 가격',
    INDEX idx_unit_type (Unit_Type),
    INDEX idx_release (`Release`)
);

-- Global: 짬통
CREATE TABLE Global (
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '고유 ID',
    Doc_Price_Minute INT COMMENT '의사 인건비 (분당)'
);

-- Procedure_Element: 단일 시술 상세 정보 테이블
CREATE TABLE Procedure_Element (
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '단일 시술 ID',
    `Release` BOOLEAN DEFAULT TRUE COMMENT '비/활성 여부',
    Class_Major VARCHAR(100) COMMENT '시술 대분류 (enum ClassMajor)',
    Class_Sub VARCHAR(100) COMMENT '시술 중분류 (enum ClassSub)',
    Class_Detail VARCHAR(100) COMMENT '시술 상세분류 (enum ClassDetail)',
    Class_Type VARCHAR(100) COMMENT '시술 속성 (enum ClassType)',
    Name VARCHAR(255) NOT NULL COMMENT '단일 시술 이름',
    Description TEXT COMMENT '단일 시술 설명',
    Position_Type VARCHAR(100) COMMENT '시술 행위자 (enum ProcedureType)',
    Cost_Time INT COMMENT '소요 시간 (분)',
    Plan_State BOOLEAN DEFAULT FALSE COMMENT '플랜 여부',
    Plan_Count INT DEFAULT 1 COMMENT '플랜 횟수',
    Consum_1_ID INT COMMENT '소모품 1 ID',
    Consum_1_Count INT DEFAULT 1 COMMENT '소모품 1 개수',
    Procedure_Cost INT COMMENT '시술 원가',
    Base_Price INT COMMENT '기준 가격',
    FOREIGN KEY (Consum_1_ID) REFERENCES Consumables(ID) ON DELETE SET NULL,
    INDEX idx_class_major (Class_Major),
    INDEX idx_class_sub (Class_Sub),
    INDEX idx_position_type (Position_Type),
    INDEX idx_release (`Release`)
);

-- Procedure_Bundle: 단일 시술을 묶은 번들 시술 정보
CREATE TABLE Procedure_Bundle (
    GroupID INT NOT NULL COMMENT '번들 그룹 ID',
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '고유 ID',
    `Release` BOOLEAN DEFAULT TRUE COMMENT '비/활성 여부',
    Name VARCHAR(255) NOT NULL COMMENT '번들 이름',
    Description TEXT COMMENT '번들 설명',
    Element_ID INT NOT NULL COMMENT '단일 시술 ID',
    Element_Cost INT COMMENT '단일 시술 원가',
    Price_Ratio FLOAT COMMENT '가격 비율',
    FOREIGN KEY (Element_ID) REFERENCES Procedure_Element(ID) ON DELETE CASCADE,
    INDEX idx_group_id (GroupID),
    INDEX idx_element_id (Element_ID),
    INDEX idx_release (`Release`)
);

-- Procedure_Sequence: 번들 및 단일 시술 순서대로 나열한 시퀀스 정보
CREATE TABLE Procedure_Sequence (
    GroupID INT NOT NULL COMMENT '시퀀스 그룹 ID',
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '고유 ID',
    `Release` BOOLEAN DEFAULT TRUE COMMENT '비/활성 여부',
    Step_Num INT NOT NULL COMMENT '시술 순서',
    Element_ID INT COMMENT '단일 시술 ID',
    Bundle_ID INT COMMENT '번들 ID',
    Procedure_Cost INT COMMENT '시술 원가',
    Price_Ratio FLOAT COMMENT '가격 비율',
    FOREIGN KEY (Element_ID) REFERENCES Procedure_Element(ID) ON DELETE CASCADE,
    FOREIGN KEY (Bundle_ID) REFERENCES Procedure_Bundle(ID) ON DELETE CASCADE,
    INDEX idx_group_id (GroupID),
    INDEX idx_step_num (Step_Num),
    INDEX idx_element_id (Element_ID),
    INDEX idx_bundle_id (Bundle_ID),
    INDEX idx_release (`Release`)
);

-- Procedure_Info: 시술 상세 정보 테이블
-- Procedure_Info_ID는 Procedure_ID에 따라 다른 테이블 참조 (조건부 참조)
CREATE TABLE Procedure_Info (
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '고유 ID',
    `Release` BOOLEAN DEFAULT TRUE COMMENT '비/활성 여부',
    Procedure_ID INT NOT NULL COMMENT '어떤 시술(Procedure)을 설명하는지 가리키는 논리적 참조 (ID)',
    Procedure_Name VARCHAR(255) NOT NULL COMMENT '시술 이름',
    Procedure_Description TEXT COMMENT '시술 설명',
    Precautions TEXT COMMENT '주의사항',
    INDEX idx_procedure_id (Procedure_ID),
    INDEX idx_release (`Release`)
);

-- Procedure: 최종 시술 상품 테이블 (가격, 유효기간 포함)
-- Procedure_ID는 Package_Type에 따라 다른 테이블 참조 (조건부 참조)
CREATE TABLE `Procedure_Product` (
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '고유 ID',
    `Release` BOOLEAN DEFAULT TRUE COMMENT '비/활성 여부',
    Package_Type VARCHAR(100) NOT NULL COMMENT '패키지 타입 (enum PackageType)',
    Procedure_ID INT NOT NULL COMMENT '시술 ID (Package_Type에 따라 참조 대상 변경 - 로직 거쳐야 함)',
    Procedure_Info_ID INT COMMENT '시술 정보 ID (Procedure_Info.ID 참조)',
    Procedure_Cost INT COMMENT '원가',
    Price INT COMMENT '정상가',
    Sell_Price INT COMMENT '판매가',
    Discount_Rate FLOAT DEFAULT 0.0 COMMENT '할인율',
    Margin INT COMMENT '마진',
    Margin_Rate FLOAT COMMENT '마진율',
    Validity_Period INT COMMENT '유효기간 (일)',
    FOREIGN KEY (Procedure_Info_ID) REFERENCES Procedure_Info(ID) ON DELETE SET NULL,
    INDEX idx_package_type (Package_Type),
    INDEX idx_procedure_id (Procedure_ID),
    INDEX idx_release (`Release`)
);

-- 기본 Enum 데이터 삽입 (실제 시술 분류에 맞게 수정)
INSERT INTO Enum (Type, Code, Name) VALUES
-- ClassMajor (시술 대분류)
('ClassMajor', '0', 'None'),
('ClassMajor', '10', '레이저'),
('ClassMajor', '20', '초음파'),
('ClassMajor', '30', '고주파'),
('ClassMajor', '40', '실리프팅'),
('ClassMajor', '50', '주사'),
('ClassMajor', '60', '필러'),

-- ClassSub (시술 중분류)
('ClassSub', '0', 'None'),
('ClassSub', '10', '리팟'),
('ClassSub', '20', '젠틀맥스'),
('ClassSub', '30', '아포지'),
('ClassSub', '40', '피코슈어'),
('ClassSub', '50', '헐리우드'),
('ClassSub', '60', '엑셀'),
('ClassSub', '70', '네오빔'),
('ClassSub', '80', '시크릿'),
('ClassSub', '90', 'CO2'),
('ClassSub', '100', '울쎄라'),
('ClassSub', '110', '슈링크'),
('ClassSub', '120', '덴서티'),
('ClassSub', '130', '리니어지'),
('ClassSub', '140', '볼뉴머'),
('ClassSub', '150', '튠페이스'),
('ClassSub', '160', '인모드'),
('ClassSub', '170', '브이로'),
('ClassSub', '180', '민트실'),
('ClassSub', '190', '슈퍼하이코'),
('ClassSub', '200', '잼버실'),
('ClassSub', '210', '리즈네'),
('ClassSub', '220', '울트라콜'),
('ClassSub', '230', '리쥬란힐러'),
('ClassSub', '240', '리쥬란HB+'),
('ClassSub', '250', '쥬베룩'),
('ClassSub', '260', 'GPC'),
('ClassSub', '270', 'DCA'),
('ClassSub', '280', '보톡스'),
('ClassSub', '290', '바디보톡스'),
('ClassSub', '300', '레티젠'),
('ClassSub', '310', '래디어스'),
('ClassSub', '320', '페이스필러'),
('ClassSub', '330', '레스틸렌'),
('ClassSub', '340', '벨로테로'),
('ClassSub', '350', '히알라제'),

-- ClassDetail (시술 상세분류)
('ClassDetail', '0', 'None'),
('ClassDetail', '10', '주름보톡스'),
('ClassDetail', '20', '미간보톡스'),
('ClassDetail', '30', '바디보톡스'),
('ClassDetail', '40', '미세필러'),

-- ClassType (시술 속성)
('ClassType', '0', 'None'),
('ClassType', '10', '제모'),
('ClassType', '20', '쁘띠'),
('ClassType', '30', '제거'),
('ClassType', '40', '색조'),
('ClassType', '50', '리프팅'),

-- ProcedureType (시술 행위자)
('ProcedureType', '0', 'None'),
('ProcedureType', '10', '의사'),
('ProcedureType', '20', '관리사'),

-- UnitType (단위 타입)
('UnitType', '0', 'None'),
('UnitType', '10', 'cc'),
('UnitType', '20', 'EA'),
('UnitType', '30', 'Shot'),

-- PackageType (패키지 타입)
('PackageType', '0', 'None'),
('PackageType', '10', '단일시술'),
('PackageType', '20', '번들'),
('PackageType', '30', '시퀀스');