function Header() {
  return (
    <header className="border-b bg-white p-4">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">사하구 AI 챗봇</h1>
          <p className="text-sm text-slate-500">반응형 민원 안내 서비스</p>
        </div>

        <button className="rounded-xl bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">
          서비스 소개
        </button>
      </div>
    </header>
  );
}

export default Header;