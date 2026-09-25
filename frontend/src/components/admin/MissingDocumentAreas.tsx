import type { MissingDocumentArea } from "../../types/adminDashboard";

type MissingDocumentAreasProps = {
  areas: MissingDocumentArea[];
};

function MissingDocumentAreas({
  areas,
}: MissingDocumentAreasProps) {
  return (
    <section className="dashboard-card dashboard-card-wide">
      <h2>문서 보완 필요 분야</h2>

      <div className="missing-document-list">
        {areas.map((item) => (
          <div className="missing-document-item" key={item.id}>
            <span className="missing-document-area">
              {item.area}
            </span>

            <strong className="missing-document-count">
              실패 질문 {item.failedCount.toLocaleString()}건
            </strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export default MissingDocumentAreas;