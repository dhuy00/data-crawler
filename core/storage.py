"""
Storage utilities for exporting crawled data.

Supports CSV, Excel, and Parquet formats.
"""
from pathlib import Path
from typing import Union
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from core.logger import logger
from config.constants import SUPPORTED_EXPORT_FORMATS, DEFAULT_EXPORT_FORMAT


class DataStorage:
    """Handles data export to multiple formats."""

    @staticmethod
    def export_dataframe(
        df: pd.DataFrame,
        output_dir: Union[str, Path],
        filename: str,
        formats: list = None,
    ) -> dict:
        """
        Export DataFrame to multiple formats.
        
        Args:
            df: DataFrame to export
            output_dir: Output directory path
            filename: Output filename (without extension)
            formats: List of formats (csv, parquet, xlsx)
            
        Returns:
            Dictionary with export results
        """
        if formats is None:
            formats = [DEFAULT_EXPORT_FORMAT]
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if df.empty:
            logger.warning(f"DataFrame is empty, skipping export to {output_dir}")
            return {}
        
        results = {}
        
        for fmt in formats:
            if fmt.lower() not in SUPPORTED_EXPORT_FORMATS:
                logger.warning(f"Unsupported format: {fmt}. Skipping.")
                continue
            
            try:
                if fmt.lower() == "csv":
                    output_file = output_dir / f"{filename}.csv"
                    df.to_csv(output_file, index=False, encoding="utf-8-sig")
                    logger.info(f"Exported {len(df)} rows to {output_file}")
                    results["csv"] = str(output_file)
                
                elif fmt.lower() == "parquet":
                    output_file = output_dir / f"{filename}.parquet"
                    table = pa.Table.from_pandas(df)
                    pq.write_table(table, output_file, compression="snappy")
                    logger.info(f"Exported {len(df)} rows to {output_file}")
                    results["parquet"] = str(output_file)
                
                elif fmt.lower() == "xlsx":
                    output_file = output_dir / f"{filename}.xlsx"
                    df.to_excel(output_file, index=False)
                    logger.info(f"Exported {len(df)} rows to {output_file}")
                    results["xlsx"] = str(output_file)
            
            except Exception as e:
                logger.error(f"Error exporting to {fmt}: {e}")
        
        return results

    @staticmethod
    def load_dataframe(
        file_path: Union[str, Path],
    ) -> pd.DataFrame:
        """
        Load DataFrame from file (auto-detect format).
        
        Args:
            file_path: Path to file
            
        Returns:
            Loaded DataFrame
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            if file_path.suffix == ".csv":
                df = pd.read_csv(file_path)
            elif file_path.suffix == ".parquet":
                df = pd.read_parquet(file_path)
            elif file_path.suffix == ".xlsx":
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            logger.info(f"Loaded {len(df)} rows from {file_path}")
            return df
        
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise
