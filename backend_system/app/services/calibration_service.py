import asyncio
import sys
import shutil
import uuid
from pathlib import Path
from typing import List
from fastapi import UploadFile, HTTPException
from app.core.config import settings
import yaml

class CalibrationService:
    def __init__(self):
        self.temp_dir = Path(settings.CALIBRATION_TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.script_path = settings.CALIBRATION_SCRIPT_PATH

    async def process_yaml_upload(self, file: UploadFile) -> str:
        """处理YAML文件上传，返回内容"""
        content = await file.read()
        try:
            # 验证YAML格式
            yaml.safe_load(content)
            return content.decode('utf-8')
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML format: {str(e)}")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be a valid text file")

    async def run_calibration_script(self, image_files: List[UploadFile]) -> str:
        """保存图片并运行标定脚本，返回生成的YAML内容"""
        # 创建本次任务的临时目录
        task_id = str(uuid.uuid4())
        task_dir = self.temp_dir / task_id
        images_dir = task_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = task_dir / "calibration.yaml"

        try:
            # 保存所有图片
            for file in image_files:
                file_path = images_dir / file.filename
                content = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content)
            
            # 构建命令
            # 假设脚本接收 --images_dir 和 --output 参数
            cmd = [
                sys.executable, 
                str(self.script_path), 
                "--images_dir", str(images_dir.absolute()),
                "--output", str(output_file.absolute())
            ]

            # 运行脚本
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else stdout.decode()
                raise Exception(f"Script execution failed: {error_msg}")

            # 读取结果
            if not output_file.exists():
                 raise Exception("Calibration script did not generate output file")
            
            with open(output_file, "r", encoding="utf-8") as f:
                result_yaml = f.read()
            
            return result_yaml

        except Exception as e:
            # 这里可以记录日志
            raise HTTPException(status_code=500, detail=f"Calibration failed: {str(e)}")
        finally:
            # 清理临时文件
            if task_dir.exists():
                shutil.rmtree(task_dir, ignore_errors=True)

calibration_service = CalibrationService()
