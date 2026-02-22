"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Upload,
  Trash2,
  RefreshCw,
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  Database,
  BookOpen,
} from "lucide-react";
import {
  adminListKnowledgeDocs,
  adminUploadKnowledgeDoc,
  adminDeleteKnowledgeDoc,
  adminReindexKnowledgeDoc,
  adminGetKnowledgeStats,
  type KnowledgeDoc,
  type KnowledgeStats,
} from "@/lib/api";

const CATEGORIES = [
  { value: "act", label: "Act" },
  { value: "rules", label: "Rules" },
  { value: "judgment", label: "Judgment" },
  { value: "circular", label: "Circular" },
  { value: "other", label: "Other" },
];

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "indexed":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
          <CheckCircle2 className="h-3 w-3" />
          Indexed
        </span>
      );
    case "indexing":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          <Loader2 className="h-3 w-3 animate-spin" />
          Indexing
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
          <AlertCircle className="h-3 w-3" />
          Failed
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-700">
          <Clock className="h-3 w-3" />
          Pending
        </span>
      );
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function KnowledgeBasePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload form state
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [category, setCategory] = useState("other");
  const [description, setDescription] = useState("");

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [docsData, statsData] = await Promise.all([
        adminListKnowledgeDocs(),
        adminGetKnowledgeStats(),
      ]);
      setDocs(docsData);
      setStats(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll for status changes if any docs are pending/indexing
  useEffect(() => {
    const hasProcessing = docs.some(
      (d) => d.index_status === "pending" || d.index_status === "indexing"
    );
    if (!hasProcessing) return;

    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [docs, loadData]);

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);

    try {
      await adminUploadKnowledgeDoc(selectedFile, category, description);
      setShowUpload(false);
      setSelectedFile(null);
      setCategory("other");
      setDescription("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Delete "${filename}"? This will also remove its chunks from the knowledge base.`)) {
      return;
    }

    try {
      await adminDeleteKnowledgeDoc(docId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const handleReindex = async (docId: string) => {
    try {
      await adminReindexKnowledgeDoc(docId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reindex failed");
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-sm text-gray-500">
            Manage legal documents for the RAG knowledge base
          </p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Upload className="h-4 w-4" />
          Upload Document
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="mb-1 inline h-4 w-4" /> {error}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <BookOpen className="h-4 w-4" />
              Total Documents
            </div>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {stats.total_documents}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              Indexed
            </div>
            <p className="mt-1 text-2xl font-bold text-green-600">
              {stats.indexed_documents}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Database className="h-4 w-4" />
              Total Chunks
            </div>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {stats.total_chunks}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Database className="h-4 w-4" />
              Qdrant Legal Vectors
            </div>
            <p className="mt-1 text-2xl font-bold text-blue-600">
              {stats.legal_collection.points_count ?? 0}
            </p>
          </div>
        </div>
      )}

      {/* Upload Form */}
      {showUpload && (
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            Upload Legal Document
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                PDF File
              </label>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="block w-full rounded-lg border border-gray-300 p-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1 file:text-sm file:font-medium file:text-blue-700"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="block w-full rounded-lg border border-gray-300 p-2 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Description (optional)
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of the document"
                className="block w-full rounded-lg border border-gray-300 p-2 text-sm"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {uploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {uploading ? "Uploading..." : "Upload & Index"}
            </button>
            <button
              onClick={() => {
                setShowUpload(false);
                setSelectedFile(null);
              }}
              className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Documents Table */}
      <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Document
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Category
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Chunks
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Size
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Uploaded
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {docs.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-12 text-center text-sm text-gray-500"
                >
                  <FileText className="mx-auto mb-2 h-8 w-8 text-gray-300" />
                  No documents uploaded yet. Upload your first legal document to
                  get started.
                </td>
              </tr>
            ) : (
              docs.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-red-500" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {doc.original_filename}
                        </p>
                        {doc.description && (
                          <p className="text-xs text-gray-500">
                            {doc.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium capitalize text-gray-700">
                      {doc.doc_category}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.index_status} />
                    {doc.index_error && (
                      <p
                        className="mt-1 max-w-[200px] truncate text-xs text-red-500"
                        title={doc.index_error}
                      >
                        {doc.index_error}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {doc.chunk_count}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatBytes(doc.file_size)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatDate(doc.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {(doc.index_status === "failed" ||
                        doc.index_status === "indexed") && (
                        <button
                          onClick={() => handleReindex(doc.id)}
                          className="rounded p-1.5 text-gray-400 hover:bg-blue-50 hover:text-blue-600"
                          title="Re-index document"
                        >
                          <RefreshCw className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() =>
                          handleDelete(doc.id, doc.original_filename)
                        }
                        className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                        title="Delete document"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
