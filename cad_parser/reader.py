from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile

import ezdxf

from cad_parser.models import CADDocument

logger = logging.getLogger(__name__)


class CADReader:
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._doc = None

    def read(self) -> CADDocument:
        ext = os.path.splitext(self._file_path)[1].lower()
        if ext == ".dxf":
            dxf_doc = ezdxf.readfile(self._file_path)
        elif ext == ".dwg":
            dxf_path = self._convert_dwg_to_dxf(self._file_path)
            dxf_doc = ezdxf.readfile(dxf_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        msp = dxf_doc.modelspace()
        header = dxf_doc.header

        metadata = {
            "dxfversion": dxf_doc.dxfversion,
            "encoding": dxf_doc.encoding,
            "measurement": str(header.get("$MEASUREMENT", "")),
            "insunits": header.get("$INSUNITS", 0),
        }

        doc = CADDocument(
            file_path=self._file_path,
            file_format=ext.lstrip("."),
            metadata=metadata,
        )
        doc._dxf_doc = dxf_doc
        return doc

    @staticmethod
    def _convert_dwg_to_dxf(dwg_path: str) -> str:
        dwg2dxf = shutil.which("dwg2dxf")
        if not dwg2dxf:
            raise RuntimeError(
                "dwg2dxf not found. Install LibreDWG:\n"
                "  git clone https://github.com/LibreDWG/libredwg.git\n"
                "  cd libredwg && autoreconf -fi && ./configure && make && make install"
            )

        tmp_dir = tempfile.mkdtemp(prefix="astradraft_")
        base = os.path.splitext(os.path.basename(dwg_path))[0]
        dxf_out = os.path.join(tmp_dir, f"{base}.dxf")

        result = subprocess.run(
            [dwg2dxf, "-o", dxf_out, dwg_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dwg2dxf failed: {result.stderr}")

        logger.info("Converted %s -> %s", dwg_path, dxf_out)
        return dxf_out
