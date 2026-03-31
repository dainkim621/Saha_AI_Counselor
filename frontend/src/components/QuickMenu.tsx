type QuickMenuProps = {
  onMenuClick: (message: string) => void;
};

const menuItems = [
  "전입신고",
  "주민센터 위치",
  "복지 서비스",
  "서류 발급",
  "교통/주차",
  "시설 예약",
];

function QuickMenu({ onMenuClick }: QuickMenuProps) {
  return (
    <div className="rounded-3xl bg-white p-5 shadow">
      <h3 className="text-lg font-bold text-slate-800">자주 찾는 메뉴</h3>

      <div className="mt-4 grid grid-cols-2 gap-3">
        {menuItems.map((item) => (
          <button
            key={item}
            onClick={() => onMenuClick(item)}  
            className="rounded-2xl bg-slate-100 px-3 py-4 text-sm hover:bg-blue-100"
          >
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

export default QuickMenu;