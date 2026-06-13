"""Smali 修改模块, 统一方法 Patch 逻辑."""

import re
from pathlib import Path
from typing import Optional, List
from apk_crack_engine.core.logger import logger


class SmaliPatcher:
    """Smali 代码修改器."""

    # 常见的验证方法模式
    VIP_METHOD_PATTERNS = [
        r'\.method.*\bisVip\b',
        r'\.method.*\bcheckPermission\b',
        r'\.method.*\bisMember\b',
        r'\.method.*\bisPremium\b',
        r'\.method.*\bcanUse\b',
        r'\.method.*\bhasPermission\b',
        r'\.method.*\bcheckLicense\b',
        r'\.method.*\bverify\w*\b',
        r'\.method.*\bisAuthorized\b',
        r'\.method.*\bisActivated\b',
    ]

    # 过期检查方法
    EXPIRED_METHOD_PATTERNS = [
        r'\.method.*\bisExpired\b',
        r'\.method.*\bisTrial\b',
        r'\.method.*\bcheckExpired\b',
        r'\.method.*\bgetRemainingDays\b',
    ]

    # 用户类型方法
    USER_TYPE_PATTERNS = [
        r'\.method.*\bgetUserType\b',
        r'\.method.*\bgetAccountType\b',
        r'\.method.*\bgetMemberLevel\b',
    ]

    def __init__(self, smali_dir: Path) -> None:
        self.smali_dir = smali_dir
        self.patched_count = 0

    def patch_all_vip_methods(self) -> int:
        """Patch 所有 VIP 相关方法返回 true.

        Returns:
            修改的文件数
        """
        count = 0
        for pattern in self.VIP_METHOD_PATTERNS:
            count += self.patch_methods(pattern, return_value="0x1")
        logger.info(f"VIP 方法 Patch 完成: {count} 个文件")
        return count

    def patch_all_expired_methods(self) -> int:
        """Patch 所有过期检查方法返回 false.

        Returns:
            修改的文件数
        """
        count = 0
        for pattern in self.EXPIRED_METHOD_PATTERNS:
            count += self.patch_methods(pattern, return_value="0x0")
        logger.info(f"过期检查方法 Patch 完成: {count} 个文件")
        return count

    def patch_all_user_type_methods(self, return_type: str = "premium") -> int:
        """Patch 所有用户类型方法返回指定字符串.

        Args:
            return_type: 返回的用户类型字符串

        Returns:
            修改的文件数
        """
        count = 0
        for pattern in self.USER_TYPE_PATTERNS:
            count += self.patch_methods_string(pattern, return_string=return_type)
        logger.info(f"用户类型方法 Patch 完成: {count} 个文件")
        return count

    def patch_methods(self, method_pattern: str, return_value: str) -> int:
        """Patch 匹配的方法返回指定值.

        Args:
            method_pattern: 方法匹配正则
            return_value: 返回值 (如 "0x1" 表示 true)

        Returns:
            修改的文件数
        """
        count = 0
        if not self.smali_dir.exists():
            return count

        for smali_file in self.smali_dir.rglob("*.smali"):
            try:
                content = smali_file.read_text(encoding="utf-8", errors="ignore")
                original = content
                content = self._patch_method_return(content, method_pattern, return_value)
                if content != original:
                    smali_file.write_text(content, encoding="utf-8")
                    count += 1
                    logger.debug(f"Patch 文件: {smali_file.name}")
            except Exception as e:
                logger.warning(f"Patch 失败 {smali_file}: {e}")

        return count

    def patch_methods_string(self, method_pattern: str, return_string: str) -> int:
        """Patch 匹配的方法返回指定字符串.

        Args:
            method_pattern: 方法匹配正则
            return_string: 返回的字符串

        Returns:
            修改的文件数
        """
        count = 0
        if not self.smali_dir.exists():
            return count

        for smali_file in self.smali_dir.rglob("*.smali"):
            try:
                content = smali_file.read_text(encoding="utf-8", errors="ignore")
                original = content
                content = self._patch_method_return_string(content, method_pattern, return_string)
                if content != original:
                    smali_file.write_text(content, encoding="utf-8")
                    count += 1
            except Exception as e:
                logger.warning(f"Patch 失败 {smali_file}: {e}")

        return count

    def patch_custom_method(self, class_name: str, method_name: str,
                           return_value: str) -> bool:
        """Patch 指定类的指定方法.

        Args:
            class_name: 类名
            method_name: 方法名
            return_value: 返回值

        Returns:
            是否成功
        """
        pattern = rf'\.method.*\b{re.escape(method_name)}\b'
        count = self.patch_methods(pattern, return_value)
        return count > 0

    def _patch_method_return(self, content: str, method_pattern: str,
                             return_value: str) -> str:
        """修改方法返回值为指定值.

        Args:
            content: Smali 内容
            method_pattern: 方法匹配正则
            return_value: 返回值

        Returns:
            修改后的内容
        """
        lines = content.split("\n")
        in_method = False
        method_start = -1
        method_end = -1
        method_lines = []

        for i, line in enumerate(lines):
            if re.search(method_pattern, line):
                in_method = True
                method_start = i
                method_lines = [line]
                continue

            if in_method:
                method_lines.append(line)
                if line.strip() == ".end method":
                    method_end = i
                    break
                # 安全检查: 方法过长则跳过
                if len(method_lines) > 500:
                    in_method = False
                    method_start = -1
                    method_lines = []

        if method_start >= 0 and method_end > 0:
            # 保留方法声明, 替换方法体为直接返回
            new_lines = lines[:method_start + 1]
            new_lines.append(f"    const/4 v0, {return_value}")
            new_lines.append("    return v0")
            new_lines.append(".end method")
            new_lines.extend(lines[method_end + 1:])
            return "\n".join(new_lines)

        return content

    def _patch_method_return_string(self, content: str, method_pattern: str,
                                    return_string: str) -> str:
        """修改方法返回值为指定字符串.

        Args:
            content: Smali 内容
            method_pattern: 方法匹配正则
            return_string: 返回字符串

        Returns:
            修改后的内容
        """
        lines = content.split("\n")
        in_method = False
        method_start = -1
        method_end = -1
        method_lines = []

        for i, line in enumerate(lines):
            if re.search(method_pattern, line):
                in_method = True
                method_start = i
                method_lines = [line]
                continue

            if in_method:
                method_lines.append(line)
                if line.strip() == ".end method":
                    method_end = i
                    break
                if len(method_lines) > 500:
                    in_method = False
                    method_start = -1
                    method_lines = []

        if method_start >= 0 and method_end > 0:
            new_lines = lines[:method_start + 1]
            new_lines.append(f'    const-string v0, "{return_string}"')
            new_lines.append("    return-object v0")
            new_lines.append(".end method")
            new_lines.extend(lines[method_end + 1:])
            return "\n".join(new_lines)

        return content

    def patch_package_name(self, old_package: str, new_package: str) -> int:
        """修改包名引用.

        Args:
            old_package: 旧包名
            new_package: 新包名

        Returns:
            修改的文件数
        """
        count = 0
        old_path = old_package.replace(".", "/")
        new_path = new_package.replace(".", "/")

        for smali_file in self.smali_dir.rglob("*.smali"):
            try:
                content = smali_file.read_text(encoding="utf-8", errors="ignore")
                original = content
                content = content.replace(old_package, new_package)
                content = content.replace(old_path, new_path)
                if content != original:
                    smali_file.write_text(content, encoding="utf-8")
                    count += 1
            except Exception as e:
                logger.warning(f"修改包名失败 {smali_file}: {e}")

        return count


__all__ = ["SmaliPatcher"]
