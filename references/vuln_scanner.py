import json, re, os, subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

class VulnSeverity(Enum):
    CRITICAL = "critical"  # 高危，可直接利用
    HIGH = "high"         # 高风险
    MEDIUM = "medium"     # 中等风险
    LOW = "low"           # 低风险
    INFO = "info"         # 信息

class VulnType(Enum):
    EXPORTED_COMPONENT = "exported_component"  # 导出组件
    INSECURE_PERMISSION = "insecure_permission"  # 不安全权限
    HARDCODED_SECRET = "hardcoded_secret"  # 硬编码密钥
    INSECURE_STORAGE = "insecure_storage"  # 不安全存储
    SSL_MISCONFIG = "ssl_misconfig"  # SSL配置错误
    DEBUGGABLE = "debuggable"  # 可调试
    BACKUP_ENABLED = "backup_enabled"  # 备份允许
    INTENT_INJECTION = "intent_injection"  # Intent注入
    SQL_INJECTION = "sql_injection"  # SQL注入
    PATH_TRAVERSAL = "path_traversal"  # 路径遍历
    WEBVIEW_RCE = "webview_rce"  # WebView RCE
    FRAGMENT_INJECTION = "fragment_injection"  # Fragment注入

@dataclass
class VulnFinding:
    type: VulnType
    severity: VulnSeverity
    title: str
    description: str
    location: str
    evidence: str
    recommendation: str
    cvss_score: float = 0.0

@dataclass
class SecurityReport:
    apk_path: str
    score: float  # 0-100
    findings: List[VulnFinding]
    summary: Dict[VulnSeverity, int]
    components: Dict[str, List[str]]

class VulnScanner:
    """漏洞扫描模块 - 组件暴露检测 + 安全评分"""
    
    def __init__(self):
        self.rules = self._load_rules()
        self.severity_weights = {
            VulnSeverity.CRITICAL: 10,
            VulnSeverity.HIGH: 7,
            VulnSeverity.MEDIUM: 4,
            VulnSeverity.LOW: 1,
            VulnSeverity.INFO: 0
        }
    
    def _load_rules(self) -> List[Dict]:
        """加载扫描规则"""
        return [
            {
                "type": VulnType.EXPORTED_COMPONENT,
                "severity": VulnSeverity.HIGH,
                "check": self._check_exported_components,
                "title": "导出组件暴露",
                "description": "Activity/Service/BroadcastReceiver/ContentProvider被导出，可能被恶意应用利用"
            },
            {
                "type": VulnType.HARDCODED_SECRET,
                "severity": VulnSeverity.CRITICAL,
                "check": self._check_hardcoded_secrets,
                "title": "硬编码敏感信息",
                "description": "代码中硬编码了API密钥、密码等敏感信息"
            },
            {
                "type": VulnType.DEBUGGABLE,
                "severity": VulnSeverity.HIGH,
                "check": self._check_debuggable,
                "title": "应用可调试",
                "description": "android:debuggable=true，允许调试器附加"
            },
            {
                "type": VulnType.BACKUP_ENABLED,
                "severity": VulnSeverity.MEDIUM,
                "check": self._check_backup,
                "title": "允许备份",
                "description": "android:allowBackup=true，应用数据可被备份提取"
            },
            {
                "type": VulnType.SSL_MISCONFIG,
                "severity": VulnSeverity.HIGH,
                "check": self._check_ssl_config,
                "title": "SSL配置错误",
                "description": "存在不安全的SSL/TLS配置，如允许所有证书"
            },
            {
                "type": VulnType.INSECURE_STORAGE,
                "severity": VulnSeverity.MEDIUM,
                "check": self._check_insecure_storage,
                "title": "不安全存储",
                "description": "敏感数据存储在不安全的位置"
            },
            {
                "type": VulnType.WEBVIEW_RCE,
                "severity": VulnSeverity.CRITICAL,
                "check": self._check_webview_rce,
                "title": "WebView RCE风险",
                "description": "WebView配置不当，可能导致远程代码执行"
            },
            {
                "type": VulnType.INTENT_INJECTION,
                "severity": VulnSeverity.HIGH,
                "check": self._check_intent_injection,
                "title": "Intent注入",
                "description": "Intent参数未经验证，可能导致权限绕过"
            },
            {
                "type": VulnType.SQL_INJECTION,
                "severity": VulnSeverity.HIGH,
                "check": self._check_sql_injection,
                "title": "SQL注入",
                "description": "ContentProvider查询未参数化，存在SQL注入"
            },
            {
                "type": VulnType.PATH_TRAVERSAL,
                "severity": VulnSeverity.MEDIUM,
                "check": self._check_path_traversal,
                "title": "路径遍历",
                "description": "文件路径未经验证，可能导致路径遍历攻击"
            }
        ]
    
    def scan(self, apk_path: str) -> SecurityReport:
        """扫描APK漏洞"""
        findings = []
        
        # 解析APK
        manifest = self._parse_manifest(apk_path)
        smali_dir = self._extract_smali(apk_path)
        
        # 执行所有规则
        for rule in self.rules:
            try:
                result = rule["check"](manifest, smali_dir, apk_path)
                if result:
                    findings.extend(result)
            except Exception as e:
                print(f"⚠️ 规则执行失败 {rule['type']}: {e}")
        
        # 计算安全评分
        score = self._calculate_score(findings)
        
        # 统计
        summary = defaultdict(int)
        for f in findings:
            summary[f.severity] += 1
        
        # 组件分析
        components = self._analyze_components(manifest)
        
        return SecurityReport(
            apk_path=apk_path,
            score=score,
            findings=findings,
            summary=dict(summary),
            components=components
        )
    
    def _parse_manifest(self, apk_path: str) -> Dict:
        """解析AndroidManifest.xml"""
        try:
            # 使用aapt2解析
            result = subprocess.run(
                ["aapt2", "dump", "xmltree", "--file", "AndroidManifest.xml", apk_path],
                capture_output=True, text=True, timeout=30
            )
            
            manifest = {
                "package": "",
                "permissions": [],
                "activities": [],
                "services": [],
                "receivers": [],
                "providers": [],
                "debuggable": False,
                "allow_backup": False,
                "uses_cleartext": False
            }
            
            # 解析输出
            for line in result.stdout.split('\n'):
                if 'package=' in line:
                    match = re.search(r'package="([^"]+)"', line)
                    if match:
                        manifest["package"] = match.group(1)
                
                elif 'android.permission.' in line:
                    match = re.search(r'android\.permission\.([A-Z_]+)', line)
                    if match:
                        manifest["permissions"].append(match.group(1))
                
                elif 'activity' in line and 'name=' in line:
                    match = re.search(r'name="([^"]+)"', line)
                    if match:
                        manifest["activities"].append(match.group(1))
                
                elif 'service' in line and 'name=' in line:
                    match = re.search(r'name="([^"]+)"', line)
                    if match:
                        manifest["services"].append(match.group(1))
                
                elif 'receiver' in line and 'name=' in line:
                    match = re.search(r'name="([^"]+)"', line)
                    if match:
                        manifest["receivers"].append(match.group(1))
                
                elif 'provider' in line and 'name=' in line:
                    match = re.search(r'name="([^"]+)"', line)
                    if match:
                        manifest["providers"].append(match.group(1))
                
                elif 'debuggable' in line:
                    manifest["debuggable"] = '0x1' in line or 'true' in line
                
                elif 'allowBackup' in line:
                    manifest["allow_backup"] = '0x1' in line or 'true' in line
                
                elif 'usesCleartextTraffic' in line:
                    manifest["uses_cleartext"] = '0x1' in line or 'true' in line
            
            return manifest
            
        except Exception as e:
            print(f"⚠️ Manifest解析失败: {e}")
            return {}
    
    def _extract_smali(self, apk_path: str) -> str:
        """提取smali代码"""
        import tempfile, zipfile
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(apk_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            # 查找classes.dex并反编译
            dex_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.dex'):
                        dex_files.append(os.path.join(root, file))
            
            # 使用baksmali反编译
            smali_dir = os.path.join(temp_dir, "smali")
            for dex in dex_files:
                subprocess.run(
                    ["baksmali", "d", dex, "-o", smali_dir],
                    capture_output=True, timeout=60
                )
            
            return smali_dir
            
        except Exception as e:
            print(f"⚠️ Smali提取失败: {e}")
            return ""
    
    def _check_exported_components(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查导出组件"""
        findings = []
        
        for comp_type in ['activities', 'services', 'receivers', 'providers']:
            for comp in manifest.get(comp_type, []):
                # 检查是否导出
                if self._is_component_exported(comp, manifest, comp_type):
                    findings.append(VulnFinding(
                        type=VulnType.EXPORTED_COMPONENT,
                        severity=VulnSeverity.HIGH,
                        title=f"导出的{comp_type[:-1]}: {comp}",
                        description=f"{comp}被导出，可能被恶意应用调用",
                        location=f"AndroidManifest.xml",
                        evidence=f"{comp} exported=true",
                        recommendation="移除不需要的exported属性，或添加权限保护"
                    ))
        
        return findings
    
    def _is_component_exported(self, comp: str, manifest: Dict, comp_type: str) -> bool:
        """判断组件是否导出"""
        # 简化的判断：主Activity默认导出，其他需要检查
        if comp_type == 'activities' and 'MainActivity' in comp:
            return True
        
        # 检查是否有intent-filter
        return True  # 简化处理
    
    def _check_hardcoded_secrets(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查硬编码密钥"""
        findings = []
        
        # 常见密钥模式
        secret_patterns = [
            (r'api[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']', "API Key"),
            (r'secret[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']', "Secret Key"),
            (r'password["\']?\s*[:=]\s*["\']([^"\']{8,})["\']', "Password"),
            (r'token["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]{20,})["\']', "Token"),
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub Token"),
        ]
        
        if not smali_dir or not os.path.exists(smali_dir):
            return findings
        
        # 扫描smali文件
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if not file.endswith('.smali'):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for pattern, secret_type in secret_patterns:
                        for match in re.finditer(pattern, content, re.IGNORECASE):
                            secret = match.group(1)
                            # 屏蔽部分密钥
                            masked = secret[:4] + "****" + secret[-4:]
                            
                            findings.append(VulnFinding(
                                type=VulnType.HARDCODED_SECRET,
                                severity=VulnSeverity.CRITICAL,
                                title=f"硬编码{secret_type}",
                                description=f"发现硬编码的{secret_type}: {masked}",
                                location=file_path,
                                evidence=masked,
                                recommendation=f"将{secret_type}移至服务端或使用Android Keystore"
                            ))
                            
                except Exception:
                    pass
        
        return findings
    
    def _check_debuggable(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查可调试"""
        if manifest.get("debuggable", False):
            return [VulnFinding(
                type=VulnType.DEBUGGABLE,
                severity=VulnSeverity.HIGH,
                title="应用可调试",
                description="android:debuggable=true，允许调试器附加",
                location="AndroidManifest.xml",
                evidence="debuggable=true",
                recommendation="发布版本必须设置debuggable=false"
            )]
        return []
    
    def _check_backup(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查备份"""
        if manifest.get("allow_backup", False):
            return [VulnFinding(
                type=VulnType.BACKUP_ENABLED,
                severity=VulnSeverity.MEDIUM,
                title="允许应用备份",
                description="android:allowBackup=true，应用数据可被adb backup提取",
                location="AndroidManifest.xml",
                evidence="allowBackup=true",
                recommendation="设置allowBackup=false或实现BackupAgent加密"
            )]
        return []
    
    def _check_ssl_config(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查SSL配置"""
        findings = []
        
        # 检查明文传输
        if manifest.get("uses_cleartext", False):
            findings.append(VulnFinding(
                type=VulnType.SSL_MISCONFIG,
                severity=VulnSeverity.HIGH,
                title="允许明文传输",
                description="usesCleartextTraffic=true，允许HTTP明文传输",
                location="AndroidManifest.xml",
                evidence="usesCleartextTraffic=true",
                recommendation="禁用明文传输，强制使用HTTPS"
            ))
        
        # 检查证书信任
        if smali_dir and os.path.exists(smali_dir):
            for root, dirs, files in os.walk(smali_dir):
                for file in files:
                    if not file.endswith('.smali'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # 检查信任所有证书
                        if 'TrustAll' in content or 'AllTrusting' in content:
                            findings.append(VulnFinding(
                                type=VulnType.SSL_MISCONFIG,
                                severity=VulnSeverity.CRITICAL,
                                title="信任所有SSL证书",
                                description="实现信任所有证书，存在中间人攻击风险",
                                location=file_path,
                                evidence="TrustAll/AllTrusting found",
                                recommendation="使用系统默认证书验证"
                            ))
                            
                    except Exception:
                        pass
        
        return findings
    
    def _check_insecure_storage(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查不安全存储"""
        findings = []
        
        if not smali_dir or not os.path.exists(smali_dir):
            return findings
        
        # 检查SharedPreferences模式
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if not file.endswith('.smali'):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 检查MODE_WORLD_READABLE/WRITEABLE
                    if 'MODE_WORLD_READABLE' in content or 'MODE_WORLD_WRITEABLE' in content:
                        findings.append(VulnFinding(
                            type=VulnType.INSECURE_STORAGE,
                            severity=VulnSeverity.MEDIUM,
                            title="不安全的SharedPreferences模式",
                            description="使用MODE_WORLD_READABLE/WRITEABLE，其他应用可访问",
                            location=file_path,
                            evidence="MODE_WORLD_READABLE/WRITEABLE",
                            recommendation="使用MODE_PRIVATE"
                        ))
                    
                    # 检查SD卡存储
                    if '/sdcard/' in content or 'getExternalStorageDirectory' in content:
                        findings.append(VulnFinding(
                            type=VulnType.INSECURE_STORAGE,
                            severity=VulnSeverity.MEDIUM,
                            title="SD卡存储敏感数据",
                            description="敏感数据存储在SD卡，可被其他应用读取",
                            location=file_path,
                            evidence="SDCard storage",
                            recommendation="使用内部存储或加密存储"
                        ))
                        
                except Exception:
                    pass
        
        return findings
    
    def _check_webview_rce(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查WebView RCE"""
        findings = []
        
        if not smali_dir or not os.path.exists(smali_dir):
            return findings
        
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if not file.endswith('.smali'):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 检查setJavaScriptEnabled
                    if 'setJavaScriptEnabled' in content and '0x1' in content:
                        # 检查是否同时有file access
                        if 'setAllowFileAccess' in content or 'setAllowUniversalAccess' in content:
                            findings.append(VulnFinding(
                                type=VulnType.WEBVIEW_RCE,
                                severity=VulnSeverity.CRITICAL,
                                title="WebView远程代码执行风险",
                                description="JavaScript启用且允许文件访问，存在RCE风险",
                                location=file_path,
                                evidence="setJavaScriptEnabled + setAllowFileAccess",
                                recommendation="禁用文件访问或使用WebAssetLoader"
                            ))
                        
                except Exception:
                    pass
        
        return findings
    
    def _check_intent_injection(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查Intent注入"""
        findings = []
        
        if not smali_dir or not os.path.exists(smali_dir):
            return findings
        
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if not file.endswith('.smali'):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 检查动态Intent启动
                    if 'getIntent' in content and 'startActivity' in content:
                        # 检查是否验证
                        if 'resolveActivity' not in content and 'getComponent' not in content:
                            findings.append(VulnFinding(
                                type=VulnType.INTENT_INJECTION,
                                severity=VulnSeverity.HIGH,
                                title="Intent注入漏洞",
                                description="直接使用未验证的Intent启动Activity",
                                location=file_path,
                                evidence="getIntent -> startActivity without validation",
                                recommendation="验证Intent来源和组件"
                            ))
                        
                except Exception:
                    pass
        
        return findings
    
    def _check_sql_injection(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查SQL注入"""
        findings = []
        
        if not smali_dir or not os.path.exists(smali_dir):
            return findings
        
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if not file.endswith('.smali'):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 检查rawQuery
                    if 'rawQuery' in content:
                        # 检查是否拼接SQL
                        if 'new-instance' in content and 'StringBuilder' in content:
                            findings.append(VulnFinding(
                                type=VulnType.SQL_INJECTION,
                                severity=VulnSeverity.HIGH,
                                title="SQL注入漏洞",
                                description="使用rawQuery拼接SQL语句",
                                location=file_path,
                                evidence="rawQuery + StringBuilder",
                                recommendation="使用参数化查询selectionArgs"
                            ))
                        
                except Exception:
                    pass
        
        return findings
    
    def _check_path_traversal(self, manifest: Dict, smali_dir: str, apk_path: str) -> List[VulnFinding]:
        """检查路径遍历"""
        findings = []
        
        if not smali_dir or not os.path.exists(smali_dir):
            return findings
        
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if not file.endswith('.smali'):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 检查ContentProvider文件访问
                    if 'openFile' in content or 'openAssetFile' in content:
                        if '..' in content or 'getLastPathSegment' in content:
                            findings.append(VulnFinding(
                                type=VulnType.PATH_TRAVERSAL,
                                severity=VulnSeverity.MEDIUM,
                                title="路径遍历漏洞",
                                description="ContentProvider文件访问未验证路径",
                                location=file_path,
                                evidence="openFile with path traversal risk",
                                recommendation="验证并规范化文件路径"
                            ))
                        
                except Exception:
                    pass
        
        return findings
    
    def _calculate_score(self, findings: List[VulnFinding]) -> float:
        """计算安全评分"""
        if not findings:
            return 100.0
        
        total_weight = sum(self.severity_weights.get(f.severity, 0) for f in findings)
        
        # 基础分100，每权重扣1分
        score = max(0, 100 - total_weight)
        
        return score
    
    def _analyze_components(self, manifest: Dict) -> Dict[str, List[str]]:
        """分析组件"""
        return {
            "activities": manifest.get("activities", []),
            "services": manifest.get("services", []),
            "receivers": manifest.get("receivers", []),
            "providers": manifest.get("providers", []),
            "permissions": manifest.get("permissions", [])
        }
    
    def generate_report(self, report: SecurityReport, format: str = "json") -> str:
        """生成报告"""
        if format == "json":
            return json.dumps({
                "apk": report.apk_path,
                "score": report.score,
                "summary": {k.value: v for k, v in report.summary.items()},
                "findings": [
                    {
                        "type": f.type.value,
                        "severity": f.severity.value,
                        "title": f.title,
                        "description": f.description,
                        "location": f.location,
                        "evidence": f.evidence,
                        "recommendation": f.recommendation,
                        "cvss": f.cvss_score
                    }
                    for f in report.findings
                ],
                "components": report.components
            }, indent=2, ensure_ascii=False)
        
        elif format == "html":
            return self._generate_html_report(report)
        
        else:
            return self._generate_text_report(report)
    
    def _generate_html_report(self, report: SecurityReport) -> str:
        """生成HTML报告"""
        # 简化的HTML报告
        color = "green" if report.score >= 80 else "orange" if report.score >= 60 else "red"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>安全扫描报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #fff; }}
        .score {{ font-size: 48px; color: {color}; }}
        .finding {{ background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .critical {{ border-left: 5px solid #ff4444; }}
        .high {{ border-left: 5px solid #ff8800; }}
        .medium {{ border-left: 5px solid #ffcc00; }}
        .low {{ border-left: 5px solid #00ccff; }}
    </style>
</head>
<body>
    <h1>安全扫描报告</h1>
    <p>APK: {report.apk_path}</p>
    <div class="score">{report.score}/100</div>
    
    <h2>发现的问题</h2>
"""
        
        for f in report.findings:
            severity_class = f.severity.value
            html += f"""
    <div class="finding {severity_class}">
        <h3>{f.title} [{f.severity.value.upper()}]</h3>
        <p>{f.description}</p>
        <p><strong>位置:</strong> {f.location}</p>
        <p><strong>建议:</strong> {f.recommendation}</p>
    </div>
"""
        
        html += "</body></html>"
        return html
    
    def _generate_text_report(self, report: SecurityReport) -> str:
        """生成文本报告"""
        text = f"""
安全扫描报告
============
APK: {report.apk_path}
评分: {report.score}/100

发现问题:
"""
        
        for f in report.findings:
            text += f"""
[{f.severity.value.upper()}] {f.title}
  {f.description}
  位置: {f.location}
  建议: {f.recommendation}
"""
        
        return text

# 便捷函数
def scan_apk(apk_path: str) -> SecurityReport:
    """快速扫描APK"""
    scanner = VulnScanner()
    return scanner.scan(apk_path)

def quick_score(apk_path: str) -> float:
    """快速获取安全评分"""
    scanner = VulnScanner()
    report = scanner.scan(apk_path)
    return report.score
