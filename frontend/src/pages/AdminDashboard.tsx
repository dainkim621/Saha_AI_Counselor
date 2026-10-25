
import "../styles/AdminDashboard.css";
import { useState, useEffect } from "react";

import SummaryCards from "../components/admin/SummaryCards";
import FailedQuestions from "../components/admin/FailedQuestions";
import HourlyUsage from "../components/admin/HourlyUsage";
import PopularQuestions from "../components/admin/PopularQuestions";
import MissingDocumentAreas from "../components/admin/MissingDocumentAreas";
import SatisfactionStats from "../components/admin/SatisfactionStats";

import type {
  HourlyUsageStat,
  PopularQuestion,
  FailedQuestion,
  MissingDocumentArea,
  SatisfactionStat,
} from "../types/adminDashboard";

const BACKEND_URL = "http://localhost:8000";

// 관리자 질문 분석 대시보드
function AdminDashboard() {

  // 요약 통계 데이터
  const [summaryData, setSummaryData] = useState({
    totalQuestions: 0,
    failedQuestionCount: 0,
    topLanguage: "로딩 중...",
    peakHour: "로딩 중...",
  });

  // 답변 실패 질문 실제 데이터
  const [failedQuestionsData, setFailedQuestionsData] =
  useState<FailedQuestion[]>([]);

  // 사용자 만족도 현황
  const [satisfactionData, setSatisfactionData] =
    useState<SatisfactionStat | null>(null);

  // 문서 보완 필요 분야 실제 데이터
  const [missingDocumentAreasData, setMissingDocumentAreasData] =
    useState<MissingDocumentArea[]>([]);

  // 시간대별 이용량 데이터
  const [hourlyUsageData, setHourlyUsageData] = useState<
    HourlyUsageStat[]
  >([]);

  // 가장 이용량이 많은 시간
  const [actualPeakHour, setActualPeakHour] =
    useState("데이터 없음");

  // 자주 묻는 질문 TOP5 실제 데이터
  const [popularQuestionsData, setPopularQuestionsData] =
    useState<PopularQuestion[]>([]);

  // 요약 통계 조회
  useEffect(() => {
    const fetchSummaryData = async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/admin/dashboard/summary`,
          {
            credentials: "include",
          }
        );

        if (response.ok) {
          const data = await response.json();

          setSummaryData({
            totalQuestions: data.totalQuestions,
            failedQuestionCount: data.failedQuestionCount,
            topLanguage: data.topLanguage,
            peakHour: data.peakHour,
          });
        }
      } catch (error) {
        console.error(
          "대시보드 통계 데이터를 불러오는 중 오류 발생:",
          error
        );
      }
    };

    fetchSummaryData();
  }, []);

  // 답변 실패 질문 조회
  useEffect(() => {
    const fetchFailedQuestions = async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/admin/dashboard/failed-questions`,
          {
            credentials: "include",
          }
        );

        if (!response.ok) {
          throw new Error("답변 실패 질문 조회 실패");
        }

        const data: FailedQuestion[] = await response.json();

        // 최신 실패 질문 3개만 표시
        setFailedQuestionsData(data.slice(0, 3));

      } catch (error) {
        console.error(
          "답변 실패 질문 조회 오류:",
          error
        );
      }
    };

    fetchFailedQuestions();
  }, []);

  // 사용자 만족도 통계 조회
  useEffect(() => {
    const fetchSatisfactionStats = async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/admin/dashboard/satisfaction`,
          {
            credentials: "include",
          }
        );

        if (!response.ok) {
          throw new Error("만족도 통계 조회 실패");
        }

        const data: SatisfactionStat = await response.json();

        setSatisfactionData(data);

      } catch (error) {
        console.error(
          "만족도 통계 조회 오류:",
          error
        );
      }
    };

    fetchSatisfactionStats();
  }, []);

  // 문서 보완 필요 분야 조회
  useEffect(() => {
    const fetchMissingDocumentAreas = async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/admin/dashboard/missing-document-areas`,
          {
            credentials: "include",
          }
        );

        if (!response.ok) {
          throw new Error("문서 보완 필요 분야 조회 실패");
        }

        const data: {
          area: string;
          count: number;
        }[] = await response.json();

        // 백엔드 응답을 프론트엔드 타입에 맞게 변환
        const formattedData: MissingDocumentArea[] =
          data.map((item, index) => ({
            id: index + 1,
            area: item.area,
            failedCount: item.count,
          }));

        setMissingDocumentAreasData(formattedData);

      } catch (error) {
        console.error(
          "문서 보완 필요 분야 조회 오류:",
          error
        );
      }
    };

    fetchMissingDocumentAreas();
  }, []);

  // 시간대별 이용량 조회
  useEffect(() => {
    const fetchHourlyUsage = async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/admin/dashboard/hourly-usage`,
          {
            credentials: "include",
          }
        );

        if (!response.ok) {
          throw new Error("시간대별 이용량 조회 실패");
        }

        const data = await response.json();

        setHourlyUsageData(data.hourlyUsage);
        setActualPeakHour(data.peakHour);

      } catch (error) {
        console.error(
          "시간대별 이용량 조회 오류:",
          error
        );
      }
    };

    fetchHourlyUsage();
  }, []);

  // 자주 묻는 질문 TOP5 조회
  useEffect(() => {
    const fetchPopularQuestions = async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/frequent-questions`
        );

        if (!response.ok) {
          throw new Error("자주 묻는 질문 조회 실패");
        }

        const data: {
          question: string;
          count: number;
        }[] = await response.json();

        const formattedData: PopularQuestion[] =
          data.map((item, index) => ({
            id: index + 1,
            question: item.question,
            count: item.count,
          }));

        setPopularQuestionsData(formattedData);

      } catch (error) {
        console.error(
          "자주 묻는 질문 조회 오류:",
          error
        );
      }
    };

    fetchPopularQuestions();
  }, []);

  return (
    <main className="admin-dashboard">

      {/* 관리자 대시보드 상단 헤더 */}
      <header className="admin-dashboard-header">

        <div className="admin-dashboard-brand">
          사하구 AI 민원 상담사
          <span>관리자 시스템</span>
        </div>

        <div className="admin-dashboard-header-row">

          <div className="admin-dashboard-title">
            <h1>관리자 질문 분석 대시보드</h1>
            <p>
              사용자 질문 통계와 답변 품질을 관리합니다.
            </p>
          </div>

        </div>
      </header>

      {/* 통계 카드 영역 */}
      <section className="dashboard-grid">

        <SummaryCards
          totalQuestions={summaryData.totalQuestions ?? 0}
          failedQuestionCount={
            summaryData.failedQuestionCount ?? 0
          }
          topLanguage={
            summaryData.topLanguage || "데이터 없음"
          }
          peakHour={actualPeakHour}
        />

        <FailedQuestions
          questions={failedQuestionsData}
        />

        <SatisfactionStats
          stats={satisfactionData}
        />

        <HourlyUsage
          stats={hourlyUsageData}
        />

        <PopularQuestions
          questions={popularQuestionsData}
        />

        <MissingDocumentAreas
          areas={missingDocumentAreasData}
        />

      </section>

    </main>
  );
}

export default AdminDashboard;
