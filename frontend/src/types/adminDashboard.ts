// 관리자 대시보드 상단 요약 통계 데이터 타입
export type DashboardSummary = {
  // 최근 7일 동안 접수된 전체 질문 수
  totalQuestions: number;

  // 답변에 실패한 질문 수
  failedQuestionCount: number;

  // 가장 많이 사용된 언어
  topLanguage: string;

  // 질문 이용량이 가장 많은 시간대
  peakHour: string;
};

// 답변 실패 질문 데이터 타입
export type FailedQuestion = {
  // 질문을 구분하기 위한 고유 번호
  id: number;

  // 사용자가 실제로 입력한 질문
  question: string;

  // 답변에 실패한 이유
  reason: string;

  // 질문이 접수된 날짜와 시간
  createdAt: string;
};

// 언어별 질문 통계 데이터 타입
export type LanguageStat = {
  // 언어 이름
  language: string;

  // 해당 언어로 들어온 질문 수
  count: number;

  // 전체 질문 중 해당 언어의 비율
  percentage: number;
};

// 시간대별 질문 이용량 데이터 타입
export type HourlyUsageStat = {
  // 시간대
  hour: string;

  // 해당 시간대에 접수된 질문 수
  count: number;
};

// 자주 묻는 질문 TOP5 데이터 타입
export type PopularQuestion = {
  // 순위를 구분하기 위한 고유 번호
  id: number;

  // 자주 입력된 질문 내용
  question: string;

  // 해당 질문이 입력된 횟수
  count: number;
};

// 문서 보완이 필요한 분야 데이터 타입
export type MissingDocumentArea = {
  // 분야를 구분하기 위한 고유 번호
  id: number;

  // 행정 업무 분야
  area: string;

  // 해당 분야에서 답변에 실패한 질문 수
  failedCount: number;
};