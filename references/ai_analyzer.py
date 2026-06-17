import os, re, json, hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ProtectionType(Enum):
    NONE = "none"
    QIHOO_360 = "qihoo_360"
    TENCENT_LEGU = "tencent_legu"
    BANGBANG = "bangbang"
    AIJIAMI = "aijiami"
    BAIDU = "baidu"
    IJiami = "ijiami"
    VMP = "vmp"
    OLLVM = "ollvm"
    PROGUARD = "proguard"
    R8 = "r8"
    DEXENCRYPT = "dex_encrypt"
    NATIVE_ENCRYPT = "native_encrypt"
    ANTI_DEBUG = "anti_debug"
    ANTI_HOOK = "anti_hook"
    ANTI_EMULATOR = "anti_emulator"
    ROOT_DETECT = "root_detect"
    SSL_PINNING = "ssl_pinning"
    UNKNOWN = "unknown"

class StrategyType(Enum):
    DIRECT = "direct"  # 直接修改
    FRIDA_HOOK = "frida_hook"  # Frida Hook
    DEX_REPAIR = "dex_repair"  # DEX修复
    NATIVE_PATCH = "native_patch"  # Native补丁
    DYNAMIC_ANALYSIS = "dynamic_analysis"  # 动态分析
    MANUAL_ANALYSIS = "manual_analysis"  # 手动分析

@dataclass
class ProtectionSignature:
    name: str
    type: ProtectionType
    patterns: List[str]  # 文件路径/类名/字符串特征
    weight: int  # 权重1-10

@dataclass
class AnalysisReport:
    apk_path: str
    protection_types: List[ProtectionType]
    confidence: Dict[ProtectionType, float]  # 0-1
    recommended_strategy: StrategyType
    difficulty: str  # easy/medium/hard/extreme
    estimated_time: str
    notes: List[str]

@dataclass
class AIReport:
    analysis: AnalysisReport
    findings: List[Dict]
    recommendations: List[str]
    auto_generated: bool

# 保护类型特征数据库
PROTECTION_DB = [
    ProtectionSignature("360加固", ProtectionType.QIHOO_360, 
        ["libjiagu.so", "libjiagu_art.so", "libprotectClass.so", "com.qihoo.util"], 10),
    ProtectionSignature("腾讯乐固", ProtectionType.TENCENT_LEGU,
        ["libshell.so", "libtup.so", "libBugly.so", "tencent.legu"], 10),
    ProtectionSignature("梆梆加固", ProtectionType.BANGBANG,
        ["libsecexe.so", "libsecmain.so", "libSecShell.so"], 10),
    ProtectionSignature("爱加密", ProtectionType.AIJIAMI,
        ["libijiami.so", "libexec.so", "libexecmain.so", "sijiami"], 10),
    ProtectionSignature("百度加固", ProtectionType.BAIDU,
        ["libbaiduprotect.so", "libbaiduprotect_x86.so"], 10),
    ProtectionSignature("VMP保护", ProtectionType.VMP,
        ["libvmp.so", "libvmpcore.so", "libtransformer.so"], 9),
    ProtectionSignature("OLLVM混淆", ProtectionType.OLLVM,
        [], 8),  # 通过代码特征识别
    ProtectionSignature("ProGuard", ProtectionType.PROGUARD,
        ["a/a/a", "b/b/b", "c/c/c"], 5),  # 短类名
    ProtectionSignature("R8", ProtectionType.R8,
        ["androidx", "kotlinx", "com.google"], 4),
    ProtectionSignature("DEX加密", ProtectionType.DEXENCRYPT,
        ["classes.dex"], 7),  # DEX文件异常
    ProtectionSignature("Native加密", ProtectionType.NATIVE_ENCRYPT,
        [".so"], 6),  # SO文件加密
    ProtectionSignature("反调试", ProtectionType.ANTI_DEBUG,
        ["ptrace", "/proc/self/status", "TracerPid"], 7),
    ProtectionSignature("反Hook", ProtectionType.ANTI_HOOK,
        ["Xposed", "Frida", "substrate"], 7),
    ProtectionSignature("模拟器检测", ProtectionType.ANTI_EMULATOR,
        ["qemu", "generic", "goldfish"], 6),
    ProtectionSignature("Root检测", ProtectionType.ROOT_DETECT,
        ["su", "Superuser", "Magisk", "/system/bin/su"], 6),
    ProtectionSignature("SSL Pinning", ProtectionType.SSL_PINNING,
        ["X509TrustManager", "SSLContext", "HostnameVerifier"], 5),
]

class AIAnalyzer:
    """AI智能分析器 - 自动识别APK保护类型和推荐策略"""
    
    def __init__(self):
        self.protection_db = PROTECTION_DB
        self.findings = []
    
    def analyze(self, apk_path: str) -> AIReport:
        """分析APK文件，返回AI报告"""
        self.findings = []
        
        # 1. 基础信息分析
        self._analyze_basic_info(apk_path)
        
        # 2. 保护类型检测
        protections = self._detect_protections(apk_path)
        
        # 3. 计算置信度
        confidence = self._calculate_confidence(protections, apk_path)
        
        # 4. 推荐策略
        strategy = self._recommend_strategy(protections, confidence)
        
        # 5. 评估难度
        difficulty, est_time = self._assess_difficulty(protections, confidence)
        
        analysis = AnalysisReport(
            apk_path=apk_path,
            protection_types=[p.type for p in protections],
            confidence=confidence,
            recommended_strategy=strategy,
            difficulty=difficulty,
            estimated_time=est_time,
            notes=[f["note"] for f in self.findings]
        )
        
        return AIReport(
            analysis=analysis,
            findings=self.findings,
            recommendations=self._generate_recommendations(analysis),
            auto_generated=True
        )
    
    def _analyze_basic_info(self, apk_path: str):
        """分析基础信息"""
        size = os.path.getsize(apk_path) / (1024*1024)  # MB
        self.findings.append({
            "type": "basic",
            "note": f"APK大小: {size:.2f} MB",
            "severity": "info"
        })
        
        # 检查是否为拆分APK
        if "split" in apk_path.lower():
            self.findings.append({
                "type": "warning",
                "note": "检测到拆分APK，需要合并分析",
                "severity": "warning"
            })
    
    def _detect_protections(self, apk_path: str) -> List[ProtectionSignature]:
        """检测保护类型"""
        detected = []
        
        # 解压APK分析
        import zipfile
        try:
            with zipfile.ZipFile(apk_path, 'r') as zf:
                namelist = zf.namelist()
                
                # 检查每个保护特征
                for sig in self.protection_db:
                    score = 0
                    for pattern in sig.patterns:
                        if any(pattern in name for name in namelist):
                            score += sig.weight
                    
                    if score > 0:
                        detected.append(sig)
                        self.findings.append({
                            "type": "protection",
                            "note": f"检测到 {sig.name} (置信度: {score})",
                            "severity": "high" if score >= 8 else "medium"
                        })
        except Exception as e:
            self.findings.append({
                "type": "error",
                "note": f"APK解析失败: {str(e)}",
                "severity": "error"
            })
        
        return detected
    
    def _calculate_confidence(self, protections: List[ProtectionSignature], 
                              apk_path: str) -> Dict[ProtectionType, float]:
        """计算每种保护类型的置信度"""
        confidence = {}
        
        for sig in protections:
            # 基于权重计算置信度
            base_conf = min(sig.weight / 10.0, 1.0)
            
            # 如果有多个特征匹配，提高置信度
            confidence[sig.type] = min(base_conf * 1.2, 1.0)
        
        if not confidence:
            confidence[ProtectionType.NONE] = 0.9
        
        return confidence
    
    def _recommend_strategy(self, protections: List[ProtectionSignature],
                          confidence: Dict[ProtectionType, float]) -> StrategyType:
        """推荐破解策略"""
        types = [p.type for p in protections]
        
        # VMP/OLLVM -> 动态分析
        if ProtectionType.VMP in types or ProtectionType.OLLVM in types:
            return StrategyType.DYNAMIC_ANALYSIS
        
        # 加固壳 -> DEX修复
        if any(t in [ProtectionType.QIHOO_360, ProtectionType.TENCENT_LEGU,
                    ProtectionType.BANGBANG, ProtectionType.AIJIAMI] for t in types):
            return StrategyType.DEX_REPAIR
        
        # Native加密 -> Native补丁
        if ProtectionType.NATIVE_ENCRYPT in types:
            return StrategyType.NATIVE_PATCH
        
        # 反调试/反Hook -> Frida Hook
        if ProtectionType.ANTI_DEBUG in types or ProtectionType.ANTI_HOOK in types:
            return StrategyType.FRIDA_HOOK
        
        # 无保护 -> 直接修改
        if ProtectionType.NONE in types:
            return StrategyType.DIRECT
        
        return StrategyType.MANUAL_ANALYSIS
    
    def _assess_difficulty(self, protections: List[ProtectionSignature],
                          confidence: Dict[ProtectionType, float]) -> Tuple[str, str]:
        """评估破解难度"""
        types = [p.type for p in protections]
        
        # 计算难度分数
        score = 0
        for t in types:
            if t in [ProtectionType.VMP, ProtectionType.OLLVM]:
                score += 10
            elif t in [ProtectionType.QIHOO_360, ProtectionType.TENCENT_LEGU,
                      ProtectionType.BANGBANG, ProtectionType.AIJIAMI]:
                score += 8
            elif t in [ProtectionType.DEXENCRYPT, ProtectionType.NATIVE_ENCRYPT]:
                score += 7
            elif t in [ProtectionType.ANTI_DEBUG, ProtectionType.ANTI_HOOK]:
                score += 5
            elif t in [ProtectionType.SSL_PINNING]:
                score += 3
            elif t in [ProtectionType.PROGUARD, ProtectionType.R8]:
                score += 2
        
        # 根据分数评估难度
        if score >= 15:
            return "extreme", "3-7天"
        elif score >= 10:
            return "hard", "1-3天"
        elif score >= 5:
            return "medium", "4-8小时"
        else:
            return "easy", "1-2小时"
    
    def _generate_recommendations(self, analysis: AnalysisReport) -> List[str]:
        """生成建议"""
        recommendations = []
        
        strategy_map = {
            StrategyType.DIRECT: "直接修改DEX/Smali代码即可",
            StrategyType.FRIDA_HOOK: "使用Frida Hook关键函数绕过验证",
            StrategyType.DEX_REPAIR: "先脱壳获取原始DEX，再修改",
            StrategyType.NATIVE_PATCH: "Patch SO文件中的验证逻辑",
            StrategyType.DYNAMIC_ANALYSIS: "需要动态调试分析VM行为",
            StrategyType.MANUAL_ANALYSIS: "建议手动分析保护机制"
        }
        
        recommendations.append(
            f"推荐策略: {strategy_map.get(analysis.recommended_strategy, '未知')}"
        )
        
        # 根据保护类型添加具体建议
        for pt in analysis.protection_types:
            if pt == ProtectionType.QIHOO_360:
                recommendations.append("360加固: 使用Frida Dump脱壳，参考360脱壳脚本")
            elif pt == ProtectionType.TENCENT_LEGU:
                recommendations.append("腾讯乐固: 使用反射调用脱壳，或内存Dump")
            elif pt == ProtectionType.VMP:
                recommendations.append("VMP保护: 需要Trace分析VM指令，难度极高")
            elif pt == ProtectionType.ANTI_DEBUG:
                recommendations.append("反调试: 使用Frida Hook ptrace绕过")
            elif pt == ProtectionType.SSL_PINNING:
                recommendations.append("SSL Pinning: 使用Frida脚本绕过证书校验")
        
        return recommendations
    
    def quick_scan(self, apk_path: str) -> Dict:
        """快速扫描，返回简要结果"""
        report = self.analyze(apk_path)
        return {
            "protections": [p.value for p in report.analysis.protection_types],
            "strategy": report.analysis.recommended_strategy.value,
            "difficulty": report.analysis.difficulty,
            "time": report.analysis.estimated_time,
            "confidence": {k.value: v for k, v in report.analysis.confidence.items()}
        }

# 便捷函数
def analyze_apk(apk_path: str) -> AIReport:
    """快速分析APK"""
    analyzer = AIAnalyzer()
    return analyzer.analyze(apk_path)

def quick_scan(apk_path: str) -> Dict:
    """快速扫描"""
    analyzer = AIAnalyzer()
    return analyzer.quick_scan(apk_path)
