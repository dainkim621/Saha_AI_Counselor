function MascotCard() {
  return (
    <div className="rounded-3xl bg-white p-5 shadow">
      <div className="flex flex-col items-center text-center">
        <div className="flex h-40 w-40 items-center justify-center rounded-full bg-sky-50 text-slate-400">
          고우니 자리
        </div>

        <h2 className="mt-4 text-xl font-bold text-slate-800">
          안녕하세요, 고우니예요!
        </h2>

        <p className="mt-2 text-sm leading-6 text-slate-500">
          복지, 민원, 시설, 생활 정보를 쉽고 친근하게 안내해드릴게요.
        </p>

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
            민원 안내
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
            복지 서비스
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
            시설 정보
          </span>
        </div>
      </div>
    </div>
  );
}

export default MascotCard;