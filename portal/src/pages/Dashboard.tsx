import { useEffect } from "react";

export default function Dashboard() {
  useEffect(() => {
    document.title = "Dashboard · TerraCipher";
  }, []);

  return (
    <div className="wrap">
      <h1 className="page-title">Dashboard</h1>
    </div>
  );
}
