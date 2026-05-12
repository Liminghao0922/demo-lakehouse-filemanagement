export async function apiGet(url) {
  const res = await fetch(url, {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error((await safeReadError(res)) || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function safeReadError(res) {
  try {
    const payload = await res.json();
    return payload.error || JSON.stringify(payload);
  } catch {
    return await res.text();
  }
}

export function uploadFiles(folder, files, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file, file.name);
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/upload?folder=${encodeURIComponent(folder)}`);
    xhr.withCredentials = true;

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onProgress) {
        return;
      }
      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress(percent);
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.responseText}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Upload failed due to a network error."));
    };

    xhr.send(formData);
  });
}

export async function downloadFiles(folder, files) {
  const res = await fetch(`/api/download?folder=${encodeURIComponent(folder)}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ files }),
  });

  if (!res.ok) {
    throw new Error((await safeReadError(res)) || `Download failed: ${res.status}`);
  }

  return res.blob();
}
