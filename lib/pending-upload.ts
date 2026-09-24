let pendingFile: File | null = null;

export function setPendingUpload(file: File) {
  pendingFile = file;
}

export function takePendingUpload() {
  const file = pendingFile;
  pendingFile = null;
  return file;
}
