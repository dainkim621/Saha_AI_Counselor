import type {
  DashboardSummary,
  FailedQuestion,
  LanguageStat,
  HourlyUsageStat,
  PopularQuestion,
  MissingDocumentArea,
} from "../types/adminDashboard";

// 관리자 대시보드 화면 개발용 임시 데이터
export const dashboardSummaryMock: DashboardSummary = {
  totalQuestions: 1284,
  failedQuestionCount: 37,
  topLanguage: "한국어",
  peakHour: "14:00 ~ 15:00",
};

// 답변 실패 질문 화면 개발용 임시 데이터
export const failedQuestionsMock: FailedQuestion[] = [
  {
    id: 1,
    question: "여권 재발급은 어디서 신청하나요?",
    reason: "관련 문서 부족",
    createdAt: "2026-09-21 14:32",
  },
  {
    id: 2,
    question: "목욕비 지원 대상은 누구인가요?",
    reason: "검색 결과 부족",
    createdAt: "2026-09-21 11:08",
  },
  {
    id: 3,
    question: "전입신고할 때 필요한 서류가 뭔가요?",
    reason: "관련 문서 부족",
    createdAt: "2026-09-20 16:45",
  },
];

// 언어별 질문 통계 화면 개발용 임시 데이터
export const languageStatsMock: LanguageStat[] = [
  {
    language: "한국어",
    count: 1050,
    percentage: 81.8,
  },
  {
    language: "영어",
    count: 120,
    percentage: 9.3,
  },
  {
    language: "중국어",
    count: 70,
    percentage: 5.5,
  },
  {
    language: "일본어",
    count: 44,
    percentage: 3.4,
  },
];

// 시간대별 이용량 화면 개발용 임시 데이터
export const hourlyUsageMock: HourlyUsageStat[] = [
  {
    hour: "09:00",
    count: 72,
  },
  {
    hour: "10:00",
    count: 95,
  },
  {
    hour: "11:00",
    count: 118,
  },
  {
    hour: "12:00",
    count: 84,
  },
  {
    hour: "13:00",
    count: 132,
  },
  {
    hour: "14:00",
    count: 186,
  },
  {
    hour: "15:00",
    count: 121,
  },
  {
    hour: "16:00",
    count: 103,
  },
  {
    hour: "17:00",
    count: 78,
  },
];

// 자주 묻는 질문 TOP5 화면 개발용 임시 데이터
export const popularQuestionsMock: PopularQuestion[] = [
  {
    id: 1,
    question: "가족관계증명서는 어디서 발급하나요?",
    count: 156,
  },
  {
    id: 2,
    question: "여권 재발급은 어떻게 하나요?",
    count: 132,
  },
  {
    id: 3,
    question: "전입신고할 때 필요한 서류가 무엇인가요?",
    count: 98,
  },
  {
    id: 4,
    question: "주민등록등본은 어디서 발급하나요?",
    count: 84,
  },
  {
    id: 5,
    question: "대형폐기물 신고는 어떻게 하나요?",
    count: 71,
  },
];

// 문서 보완 필요 분야 화면 개발용 임시 데이터
export const missingDocumentAreasMock: MissingDocumentArea[] = [
  {
    id: 1,
    area: "여권",
    failedCount: 12,
  },
  {
    id: 2,
    area: "복지",
    failedCount: 9,
  },
  {
    id: 3,
    area: "전입·주소",
    failedCount: 7,
  },
  {
    id: 4,
    area: "폐기물",
    failedCount: 5,
  },
];