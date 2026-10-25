
import { useEffect, useState } from "react";

import "../styles/AdminDashboard.css";
import "../styles/AdminManagement.css";

const BACKEND_URL = "http://localhost:8000";

/* 관리자 계정 정보 타입 */
interface AdminAccount {
  id: number;
  username: string;
  name: string;
  is_active: boolean;
  is_super_admin: boolean;
  created_at: string;
  is_current: boolean;
}

/* 관리자 목록 API 응답 타입 */
interface AdminListResponse {
  admins: AdminAccount[];
}

/* 초대 코드 발급 이력 타입 */
interface AdminInviteHistory {
  id: number;
  created_by: number;
  created_at: string | null;
  expires_at: string;
  is_used: boolean;
  status: "available" | "used" | "expired";
}

/* 초대 코드 발급 이력 API 응답 타입 */
interface AdminInviteHistoryResponse {
  total_invites: number;
  available_count: number;
  invites: AdminInviteHistory[];
}


// 관리자 계정 및 초대 코드 관리 페이지
function AdminManagement() {

  /* =========================================
     초대 코드 발급 상태
  ========================================= */

  // 발급된 초대 코드
  const [inviteCode, setInviteCode] = useState("");

  // 초대 코드 만료 시간
  const [expiresAt, setExpiresAt] = useState("");

  // 초대 코드 발급 중인지 확인
  const [isIssuing, setIsIssuing] = useState(false);

  // 초대 코드 발급 오류 메시지
  const [inviteError, setInviteError] = useState("");

  
  // 초대 코드 발급 이력
  const [inviteHistory, setInviteHistory] = useState<
    AdminInviteHistory[]
  >([]);

  // 현재 사용 가능한 초대 코드 개수
  const [availableInviteCount, setAvailableInviteCount] =
    useState<number | null>(null);

  // 이력 조회 로딩 상태
  const [isInviteHistoryLoading, setIsInviteHistoryLoading] =
    useState(false);

  // 이력 조회 오류 메시지
  const [inviteHistoryError, setInviteHistoryError] =
    useState("");

  // 초대 코드 발급 후 이력 새로고침용
  const [inviteRefreshKey, setInviteRefreshKey] = useState(0);

  /* =========================================
     관리자 계정 목록 조회
  ========================================= */

  // 관리자 계정 목록
  const [adminList, setAdminList] = useState<AdminAccount[]>([]);

  // 목록 로딩 상태
  const [isAdminLoading, setIsAdminLoading] = useState(true);

  // 목록 조회 오류
  const [adminListError, setAdminListError] = useState("");

  
  // 현재 상태 변경 중인 관리자 ID
  const [updatingAdminId, setUpdatingAdminId] = useState<number | null>(null);

  // 계정 상태 변경 오류
  const [adminStatusError, setAdminStatusError] = useState("");


  // 관리자 관리 페이지 진입 시 계정 목록 조회
  useEffect(() => {
    let cancelled = false;

    const fetchAdminList = async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/admin/admins`,
          {
            method: "GET",
            credentials: "include",
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error(
              "로그인 세션이 만료되었습니다. 다시 로그인해 주세요."
            );
          }

          if (response.status === 403) {
            throw new Error(
              "관리자 목록 조회 권한이 없습니다."
            );
          }

          throw new Error(
            "관리자 목록 조회에 실패했습니다."
          );
        }

        const data: AdminListResponse =
          await response.json();

        if (!cancelled) {
          setAdminList(data.admins);
          setAdminListError("");
        }

      } catch (error) {
        if (!cancelled) {
          console.error(
            "관리자 목록 조회 오류:",
            error
          );

          setAdminListError(
            error instanceof Error
              ? error.message
              : "관리자 목록 조회 중 오류가 발생했습니다."
          );
        }
      } finally {
        if (!cancelled) {
          setIsAdminLoading(false);
        }
      }
    };

    fetchAdminList();

    return () => {
      cancelled = true;
    };
  }, []);

  // 전체 관리자 수
  const totalAdmins = adminList.length;

  // 활성 관리자 수
  const activeAdmins = adminList.filter(
    (admin) => admin.is_active
  ).length;

  // 현재 로그인한 관리자
  const currentAdmin = adminList.find(
    (admin) => admin.is_current
  );

  // 최고 관리자 권한 여부
  const isSuperAdmin =
    currentAdmin?.is_super_admin === true;
  
  /* =========================================
     초대 코드 발급 이력 조회
    ========================================= */

  useEffect(() => {
    // 관리자 목록 조회가 끝날 때까지 대기
    if (isAdminLoading) return;

    // 최고 관리자가 아니면 이력 조회하지 않음
    if (!isSuperAdmin) {
      setInviteHistory([]);
      setAvailableInviteCount(null);
      setInviteHistoryError("");
      setIsInviteHistoryLoading(false);
      return;
    }

    let cancelled = false;

    const fetchInviteHistory = async () => {
      setIsInviteHistoryLoading(true);
      setInviteHistoryError("");

      try {
        const response = await fetch(
          `${BACKEND_URL}/admin/invites/history`,
          {
            method: "GET",
            credentials: "include",
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error(
              "로그인 세션이 만료되었습니다. 다시 로그인해 주세요."
            );
          }

          if (response.status === 403) {
            throw new Error(
              "초대 코드 이력 조회 권한이 없습니다."
            );
          }

          throw new Error(
            "초대 코드 발급 이력을 불러오지 못했습니다."
          );
        }

        const data: AdminInviteHistoryResponse =
          await response.json();

        if (!cancelled) {
          setInviteHistory(data.invites);

          // 백엔드에서 계산한 사용 가능한 초대 코드 수 저장
          setAvailableInviteCount(data.available_count);
        }

      } catch (error) {
        if (!cancelled) {
          console.error(
            "초대 코드 이력 조회 오류:",
            error
          );

          // 조회 실패 시 기존 초대 코드 개수 초기화
          setAvailableInviteCount(null);

          setInviteHistoryError(
            error instanceof Error
              ? error.message
              : "초대 코드 이력 조회 중 오류가 발생했습니다."
          );
        }
      } finally {
        if (!cancelled) {
          setIsInviteHistoryLoading(false);
        }
      }
    };

    fetchInviteHistory();

    return () => {
      cancelled = true;
    };
  }, [isAdminLoading, isSuperAdmin, inviteRefreshKey]);

  /* =========================================
     초대 코드 발급 함수
  ========================================= */

  const handleCreateInvite = async () => {
    // 중복 발급 요청 방지
    if (isIssuing) return;

    setIsIssuing(true);
    setInviteError("");
    setInviteCode("");
    setExpiresAt("");

    try {
      const response = await fetch(
        `${BACKEND_URL}/admin/invites`,
        {
          method: "POST",
          credentials: "include",
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error(
            "관리자 로그인 세션이 만료되었습니다. 다시 로그인해 주세요."
          );
        }

        if (response.status === 403) {
          throw new Error(
            "초대 코드 발급 권한이 없습니다."
          );
        }

        throw new Error(
          "초대 코드 발급에 실패했습니다."
        );
      }

      const data = await response.json();

      // 백엔드에서 발급한 실제 초대 코드 저장
      setInviteCode(data.invite_code);

      // 초대 코드 만료 시간 저장
      setExpiresAt(data.expires_at);

      // 새 코드 발급 후 초대 코드 이력 갱신
      setInviteRefreshKey((prev) => prev + 1);

    } catch (error) {
      console.error(
        "초대 코드 발급 요청 실패:",
        error
      );

      setInviteError(
        error instanceof Error
          ? error.message
          : "초대 코드 발급 중 오류가 발생했습니다."
      );
    } finally {
      setIsIssuing(false);
    }
  };

   
  /* =========================================
   관리자 계정 활성화 / 비활성화
   ========================================= */

  const handleUpdateAdminStatus = async (
    adminId: number,
    newStatus: boolean
  ) => {
    // 상태 변경 중 중복 요청 방지
    if (updatingAdminId !== null) return;

    // 최고 관리자만 변경 가능
    if (!isSuperAdmin) return;

    // 변경 대상 조회
    const targetAdmin = adminList.find(
      (admin) => admin.id === adminId
    );

    if (
      !targetAdmin ||
      targetAdmin.is_current ||
      targetAdmin.is_super_admin
    ) {
      return;
    }

    // 비활성화 시 확인
    if (!newStatus) {
      const confirmed = window.confirm(
        `${targetAdmin.name} 관리자 계정을 비활성화하시겠습니까?\n` +
        "해당 관리자는 다시 활성화하기 전까지 로그인할 수 없습니다."
      );

      if (!confirmed) return;
    }

    setUpdatingAdminId(adminId);
    setAdminStatusError("");

    try {
      const response = await fetch(
        `${BACKEND_URL}/admin/admins/${adminId}/status`,
        {
          method: "PATCH",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            is_active: newStatus,
          }),
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error(
            "로그인 세션이 만료되었습니다. 다시 로그인해 주세요."
          );
        }

        if (response.status === 403) {
          throw new Error(
            "관리자 계정 상태를 변경할 권한이 없습니다."
          );
        }

        if (response.status === 404) {
          throw new Error(
            "해당 관리자 계정을 찾을 수 없습니다."
          );
        }

        throw new Error(
          "관리자 계정 상태 변경에 실패했습니다."
        );
      }

      const data = await response.json();

      // 변경 성공 시 관리자 목록 상태 갱신
      setAdminList((prev) =>
        prev.map((admin) =>
          admin.id === adminId
            ? {
                ...admin,
                is_active: data.admin.is_active,
              }
            : admin
        )
      );

    } catch (error) {
      console.error(
        "관리자 계정 상태 변경 오류:",
        error
      );

      setAdminStatusError(
        error instanceof Error
          ? error.message
          : "계정 상태 변경 중 오류가 발생했습니다."
      );
    } finally {
      setUpdatingAdminId(null);
    }
  };

  /* =========================================
     관리자 관리 페이지 UI
  ========================================= */

  return (
    <main className="admin-dashboard admin-management">

      {/* 페이지 상단 */}
      <header className="admin-dashboard-header">
        <div className="admin-dashboard-header-row">
          <div className="admin-dashboard-title">
            <h1>관리자 관리</h1>
            <p>
              관리자 계정과 초대 코드를 관리합니다.
            </p>
          </div>
        </div>
      </header>


      {/* =====================================
          관리자 현황 요약
      ===================================== */}

      <section className="admin-management-summary">

        {/* 전체 관리자 */}
        <div className="admin-management-summary-card">
          <span>전체 관리자</span>

          <strong>
            {isAdminLoading || adminListError
              ? "—"
              : totalAdmins}
          </strong>

          <p>등록된 관리자 계정</p>
        </div>

        {/* 활성 관리자 */}
        <div className="admin-management-summary-card">
          <span>활성 관리자</span>

          <strong>
            {isAdminLoading || adminListError
              ? "—"
              : activeAdmins}
          </strong>

          <p>현재 이용 가능한 계정</p>
        </div>

        {/* 미사용 초대 코드 */}
        <div className="admin-management-summary-card">
          <span>미사용 초대 코드</span>

          <strong>
            {!isSuperAdmin ||
            isInviteHistoryLoading ||
            inviteHistoryError ||
            availableInviteCount === null
              ? "—"
              : availableInviteCount}
          </strong>

          <p>사용 가능한 초대 코드</p>
        </div>

      </section>


      {/* =====================================
          관리자 계정 목록
      ===================================== */}

      <section className="admin-management-card">

        <div className="admin-management-card-header">
          <div>
            <h2>관리자 계정 목록</h2>
            <p>
              등록된 관리자 계정과 상태를 확인합니다.
            </p>
          </div>
        </div>

        <div className="admin-management-table-wrapper">
          <table className="admin-management-table">

            <thead>
              <tr>
                <th>이름</th>
                <th>아이디</th>
                <th>가입일</th>
                <th>상태</th>
                <th>관리</th>
              </tr>
            </thead>

            <tbody>
              {isAdminLoading ? (

                /* 관리자 목록 로딩 */
                <tr>
                  <td
                    colSpan={5}
                    className="admin-management-empty"
                  >
                    관리자 계정 목록을 불러오는 중입니다.
                  </td>
                </tr>

              ) : adminListError ? (

                /* 관리자 목록 조회 오류 */
                <tr>
                  <td
                    colSpan={5}
                    className="admin-management-empty"
                    role="alert"
                  >
                    {adminListError}
                  </td>
                </tr>

              ) : adminList.length === 0 ? (

                /* 관리자 계정이 없는 경우 */
                <tr>
                  <td
                    colSpan={5}
                    className="admin-management-empty"
                  >
                    등록된 관리자 계정이 없습니다.
                  </td>
                </tr>

              ) : (

                /* 실제 관리자 계정 목록 */
                adminList.map((admin) => (
                  <tr key={admin.id}>

                    {/* 관리자 이름 */}
                    <td>
                      {admin.name}

                      {/* 현재 로그인한 관리자 */}
                      {admin.is_current && (
                        <span className="admin-management-current">
                          본인
                        </span>
                      )}
                    </td>

                    {/* 관리자 아이디 */}
                    <td>
                      {admin.username}
                    </td>

                    {/* 관리자 가입일 */}
                    <td>
                      {admin.created_at
                        ? new Date(
                            admin.created_at
                          ).toLocaleDateString(
                            "ko-KR",
                            {
                              timeZone: "Asia/Seoul",
                            }
                          )
                        : "-"}
                    </td>

                    {/* 관리자 계정 상태 */}
                    <td>
                      <span
                        className={`admin-management-status ${
                          admin.is_active
                            ? "active"
                            : "inactive"
                        }`}
                      >
                        {admin.is_active
                          ? "활성"
                          : "비활성"}
                      </span>
                    </td>
                    
                    {/* 관리자 계정 관리 기능 */}
                    <td>
                    {!isSuperAdmin ? (
                        // 일반 관리자는 계정 상태를 변경할 수 없음
                        <span className="admin-management-pending">
                        권한 없음
                        </span>
                    ) : admin.is_current || admin.is_super_admin ? (
                        // 본인 또는 최고 관리자 계정 보호
                        <span className="admin-management-pending">
                        변경 불가
                        </span>
                    ) : (
                        // 최고 관리자가 일반 관리자 계정 관리
                        <button
                        type="button"
                        className={`admin-management-status-button ${
                            admin.is_active ? "deactivate" : "activate"
                        }`}
                        onClick={() =>
                            handleUpdateAdminStatus(
                            admin.id,
                            !admin.is_active
                            )
                        }
                        disabled={updatingAdminId !== null}
                        >
                        {updatingAdminId === admin.id
                            ? "처리 중..."
                            : admin.is_active
                            ? "비활성화"
                            : "활성화"}
                        </button>
                    )}
                    </td>

                  </tr>
                ))

              )}
            </tbody>

          </table>
        </div>
        {adminStatusError && (
          <p
              className="admin-management-invite-error"
              role="alert"
          >
              {adminStatusError}
          </p>
          )}

      </section>


      {/* =====================================
          신규 관리자 초대
      ===================================== */}

      <section className="admin-management-card">

        <div className="admin-management-card-header">
          <div>
            <h2>신규 관리자 초대</h2>
            <p>
              초대 코드를 발급하여 신규 관리자의
              회원가입을 허용합니다.
            </p>
          </div>
        </div>

        <div className="admin-management-invite">

          <div className="admin-management-invite-info">
            <strong>관리자 초대 코드</strong>
            <p>
              발급된 초대 코드는 신규 관리자가
              회원가입할 때 사용합니다.
            </p>
          </div>

          {/* 초대 코드 발급 버튼 */}
          <button
            type="button"
            className="admin-management-primary-button"
            onClick={handleCreateInvite}
            disabled={isIssuing}
          >
            {isIssuing
              ? "발급 중..."
              : "초대 코드 발급"}
          </button>

        </div>


        {/* ===================================
            초대 코드 발급 결과
        =================================== */}

        <div aria-live="polite">

          {inviteCode && (
            <div className="admin-management-invite-result">

              <h3>
                초대 코드가 발급되었습니다.
              </h3>

              <p>
                아래 코드를 신규 관리자에게 전달해 주세요.
              </p>

              {/* 실제 초대 코드 */}
              <div className="admin-management-invite-code">

                <code>{inviteCode}</code>

                {/* 초대 코드 복사 */}
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(
                        inviteCode
                      );

                      alert(
                        "초대 코드가 복사되었습니다."
                      );
                    } catch {
                      alert(
                        "복사에 실패했습니다. 코드를 직접 복사해 주세요."
                      );
                    }
                  }}
                >
                  복사
                </button>

              </div>

              {/* 초대 코드 만료 시간 */}
              <p className="admin-management-invite-expiry">
                만료 시간:{" "}
                {expiresAt
                  ? new Date(expiresAt).toLocaleString(
                      "ko-KR",
                      {
                        timeZone: "Asia/Seoul",
                      }
                    )
                  : "-"}
              </p>

              {/* 초대 코드 주의사항 */}
              <p className="admin-management-invite-warning">
                초대 코드는 1회만 사용할 수 있으며,
                이 화면을 벗어나면 다시 확인할 수 없습니다.
              </p>

            </div>
          )}

          {/* 초대 코드 발급 오류 */}
          {inviteError && (
            <p
              className="admin-management-invite-error"
              role="alert"
            >
              {inviteError}
            </p>
          )}

        </div>

      </section>


      {/* =====================================
          초대 코드 발급 이력
      ===================================== */}

      <section className="admin-management-card">

        <div className="admin-management-card-header">
          <div>
            <h2>초대 코드 발급 이력</h2>
            <p>
              초대 코드의 발급일, 만료일 및
              사용 여부를 확인합니다.
            </p>
          </div>
        </div>

        <div className="admin-management-table-wrapper">
          <table className="admin-management-table">

            <thead>
              <tr>
                <th>발급일</th>
                <th>만료일</th>
                <th>상태</th>
                <th>관리</th>
              </tr>
            </thead>
            
            <tbody>
            {isAdminLoading || isInviteHistoryLoading ? (
                <tr>
                <td colSpan={4} className="admin-management-empty">
                    초대 코드 발급 이력을 불러오는 중입니다.
                </td>
                </tr>
            ) : !isSuperAdmin ? (
                <tr>
                <td colSpan={4} className="admin-management-empty">
                    초대 코드 발급 이력은 최고 관리자만
                    조회할 수 있습니다.
                </td>
                </tr>
            ) : inviteHistoryError ? (
                <tr>
                <td
                    colSpan={4}
                    className="admin-management-empty"
                    role="alert"
                >
                    {inviteHistoryError}
                </td>
                </tr>
            ) : inviteHistory.length === 0 ? (
                <tr>
                <td colSpan={4} className="admin-management-empty">
                    발급된 초대 코드가 없습니다.
                </td>
                </tr>
            ) : (
                inviteHistory.map((invite) => (
                <tr key={invite.id}>

                    {/* 발급일 */}
                    <td>
                    {invite.created_at
                        ? new Date(invite.created_at).toLocaleString(
                            "ko-KR",
                            { timeZone: "Asia/Seoul" }
                        )
                        : "-"}
                    </td>

                    {/* 만료일 */}
                    <td>
                    {new Date(invite.expires_at).toLocaleString(
                        "ko-KR",
                        { timeZone: "Asia/Seoul" }
                    )}
                    </td>

                    {/* 초대 코드 상태 */}
                    <td>
                    <span
                        className={`admin-management-invite-status ${invite.status}`}
                    >
                        {invite.status === "available"
                        ? "사용 가능"
                        : invite.status === "used"
                            ? "사용 완료"
                            : "만료"}
                    </span>
                    </td>

                    {/* 초대 코드 관리 기능 */}
                    <td>
                    <span className="admin-management-pending">
                        {invite.status === "available"
                        ? "취소 기능 준비 중"
                        : "—"}
                    </span>
                    </td>

                </tr>
                ))
            )}
            </tbody>


          </table>
        </div>

      </section>

    </main>
  );
}

export default AdminManagement;
