import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiGet, downloadFiles, uploadFiles } from "../apiClient";

export default function HomePage() {
  const navigate = useNavigate();
  const [sessionReady, setSessionReady] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [user, setUser] = useState("-");
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [files, setFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState({});
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [loadingFolders, setLoadingFolders] = useState(true);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState("");

  const isDev = import.meta.env.DEV || import.meta.env.MODE === "development";
  const hasSelection = useMemo(() => Object.values(selectedFiles).some(Boolean), [selectedFiles]);

  // Check session and load data
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoadingFolders(true);
        const profile = await apiGet("/api/profile");
        const foldersData = await apiGet("/api/folders");
        if (mounted) {
          setSessionReady(true);
          setUser(profile.user);
          setFolders(foldersData.folders || []);
        }
      } catch (err) {
        if (mounted) {
          setSessionReady(false);
          setError(err.message || "Failed to load page.");
        }
      } finally {
        if (mounted) {
          setCheckingSession(false);
          setLoadingFolders(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const loadFolder = async (folderName) => {
    setError("");
    setSelectedFolder(folderName);
    setSelectedFiles({});
    setLoadingFiles(true);
    try {
      const data = await apiGet(`/api/files?folder=${encodeURIComponent(folderName)}`);
      setFiles(data.files || []);
    } catch (err) {
      setError(err.message || "Failed to list files.");
    } finally {
      setLoadingFiles(false);
    }
  };

  const toggleSelect = (fileName) => {
    setSelectedFiles((prev) => ({ ...prev, [fileName]: !prev[fileName] }));
  };

  const onUpload = async (event) => {
    const payload = event.target.files;
    if (!payload || payload.length === 0 || !selectedFolder) {
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    setError("");
    try {
      await uploadFiles(selectedFolder, payload, setUploadProgress);
      const data = await apiGet(`/api/files?folder=${encodeURIComponent(selectedFolder)}`);
      setFiles(data.files || []);
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const onDownload = async () => {
    const names = Object.entries(selectedFiles)
      .filter(([, checked]) => checked)
      .map(([name]) => name);

    if (names.length === 0 || !selectedFolder) {
      return;
    }

    setError("");
    try {
      const blob = await downloadFiles(selectedFolder, names);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "selected-files.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || "Download failed.");
    }
  };

  const handleSignOut = () => {
    window.location.href = "/.auth/logout";
  };

  if (checkingSession) {
    return (
      <main className="shell">
        <div style={{ textAlign: "center", padding: "40px" }}>
          <div className="spinner"></div>
          <p>Loading...</p>
        </div>
      </main>
    );
  }

  if (!sessionReady) {
    return (
      <main className="shell">
        <section className="card error">
          <h2>Authentication Required</h2>
          <p>Your SWA session is not ready. Please create a new session.</p>
          <div className="actions">
            <button className="btn" onClick={() => (window.location.href = "/.auth/login/aad?post_login_redirect_uri=/")}>
              Create SWA Session
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="app-header">
        <h1 className="app-title">OneLake Browser</h1>
        <div className="user-menu">
          <span className="user-name">{user}</span>
          <button className="btn btn-icon" onClick={handleSignOut} title="Sign out">
            ↗
          </button>
        </div>
      </header>

      {isDev && (
        <section className="card dev-info">
          <h3>Development Info</h3>
          <div className="kv">
            <span>SWA Session</span>
            <strong>Ready</strong>
          </div>
          <div className="kv">
            <span>Authenticated User</span>
            <strong>{user}</strong>
          </div>
        </section>
      )}

      <section className="card">
        <h2>Available Folders</h2>
        {loadingFolders ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <span>Loading accessible folders...</span>
          </div>
        ) : (
          <div className="actions">
            {folders.map((folder) => (
              <button key={folder} className={`btn ${selectedFolder === folder ? "btn-active" : ""}`} onClick={() => loadFolder(folder)} disabled={loadingFiles}>
                {folder}
              </button>
            ))}
            {folders.length === 0 && <span className="hint">No folders available.</span>}
          </div>
        )}
      </section>

      {selectedFolder && (
        <section className="card">
          <div className="panel-head">
            <h2>Files in {selectedFolder}</h2>
            <div className="actions">
              <label className="btn" htmlFor="uploadInput">Upload Files</label>
              <input id="uploadInput" type="file" multiple onChange={onUpload} className="hidden" disabled={!selectedFolder || uploading} />
              <button className="btn btn-ghost" disabled={!hasSelection} onClick={onDownload}>Download Selected (ZIP)</button>
            </div>
          </div>

          {loadingFiles ? (
            <div className="loading-container" style={{ padding: "40px 0", textAlign: "center" }}>
              <div className="spinner"></div>
              <span>Loading files...</span>
            </div>
          ) : (
            <>
              {uploading && (
                <div className="progress-wrap">
                  <div className="progress-bar" style={{ width: `${uploadProgress}%` }} />
                  <span className="progress-text">{uploadProgress}%</span>
                </div>
              )}

              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>File Name</th>
                    <th>Modified Time</th>
                    <th>Type</th>
                    <th className="right">Size (Bytes)</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr key={file.name}>
                      <td>
                        <input type="checkbox" checked={!!selectedFiles[file.name]} onChange={() => toggleSelect(file.name)} />
                      </td>
                      <td>{file.name}</td>
                      <td>{file.modifiedTime || "-"}</td>
                      <td>{file.type || "file"}</td>
                      <td className="right">{file.size || 0}</td>
                    </tr>
                  ))}
                  {files.length === 0 && (
                    <tr>
                      <td colSpan={5} className="hint">No files in this folder.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </>
          )}
        </section>
      )}

      {error && (
        <section className="card error">
          {error}
          <div className="actions" style={{ marginTop: "10px" }}>
            <button className="btn" onClick={() => (window.location.href = "/.auth/login/aad?post_login_redirect_uri=/")}>
              Sign in to SWA
            </button>
          </div>
        </section>
      )}
    </main>
  );
}
