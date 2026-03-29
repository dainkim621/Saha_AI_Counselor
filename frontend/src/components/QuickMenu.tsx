const menuItems = [
  "전입신고",
  "주민센터 위치",
  "복지 서비스",
  "서류 발급",
  "교통/주차",
  "시설 예약",
];

function QuickMenu() {
  return (
    <div className="rounded-3xl bg-white p-5 shadow">
      <h3 className="text-lg font-bold text-slate-800">자주 찾는 메뉴</h3>
      <p className="mt-1 text-sm text-slate-500">
        자주 묻는 민원을 빠르게 확인할 수 있어요.
      </p>

      <div className="mt-4 grid grid-cols-2 gap-3">
        {menuItems.map((item) => (
          <button
            key={item}
            className="rounded-2xl bg-slate-100 px-3 py-4 text-sm font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-600"
          >
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

export default QuickMenu;