"""Build a tar.gz whose bytes depend only on file names and contents (sorted entries, zeroed mtime/owner/mode, no gzip name or timestamp)."""
import gzip, io, os, tarfile

def deterministic_targz(src_dir, out_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as t:
        for root, dirs, files in os.walk(src_dir):
            dirs.sort()
            for name in sorted(files):
                p = os.path.join(root, name); ti = t.gettarinfo(p)
                ti.mtime = 0; ti.uid = ti.gid = 0; ti.uname = ti.gname = ""; ti.mode = 0o644
                with open(p, "rb") as f: t.addfile(ti, f)
    with open(out_path, "wb") as raw:
        gz = gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0)      # filename="" stops the output path leaking into the header
        gz.write(buf.getvalue()); gz.close()
