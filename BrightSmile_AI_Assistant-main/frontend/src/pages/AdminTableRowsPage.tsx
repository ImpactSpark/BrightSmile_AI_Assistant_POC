import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, getAdminTableRows } from "../api/client";

export function AdminTableRowsPage() {
  const { tableName = "" } = useParams<{ tableName: string }>();
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAdminTableRows(tableName)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load table rows."))
      .finally(() => setLoading(false));
  }, [tableName]);

  if (loading)
    return (
      <p className="chat-panel__empty">
        <span className="app__spinner" /> Loading…
      </p>
    );
  if (error)
    return (
      <p className="app__error" role="alert">
        {error}
      </p>
    );

  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div className="gallery app__fade-in">
      <Link className="gallery__back" to="/admin">
        ← Back to admin
      </Link>
      <h2>
        {tableName} (top {rows.length} row{rows.length === 1 ? "" : "s"})
      </h2>
      {rows.length === 0 ? (
        <p>No rows in this table.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="admin-table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {columns.map((col) => (
                    <td key={col}>{JSON.stringify(row[col])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
