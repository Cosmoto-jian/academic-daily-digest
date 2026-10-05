# 关键词过滤词表（标题 contains，不区分大小写）

## 3-Broad 综合刊过滤（宁宽勿严）
protein OR membrane OR "ion channel" OR mechanosensitive OR Piezo OR gating OR allosteric OR allostery OR "elastic network" OR "normal mode" OR "molecular dynamics" OR "protein language" OR AlphaFold OR ESM OR "inverse folding" OR "protein design" OR mutation OR "variant effect" OR "conformational" OR "protein dynamics" OR "mechanical" OR "nonlinear dynamics" OR "AI for science" OR "foundation model"

## arXiv A（蛋白 AI/结构预测/突变效应）——可用作客户端过滤
"protein language model" | ESM-2 | ESM2 | ESMFold | ProteinMPNN | "inverse folding" | AlphaFold | "variant effect" | "mutation effect" | "deep mutational scanning" | "protein design" | "protein stability"
适用分类：q-bio.BM, q-bio.QM, cs.LG, cs.AI

## arXiv B（蛋白力学/构象动力学/膜蛋白）
mechanosensitive | Piezo1 | MscL | MscS | "ion channel" | "channel gating" | "membrane protein" | "elastic network" | "normal mode" | allostery | allosteric | "protein dynamics" | "conformational change" | "conformational ensemble" | "coarse-grained" | ("nonlinear dynamics" AND protein)
适用分类：q-bio.BM, physics.bio-ph, cond-mat.soft, physics.comp-ph, cond-mat.stat-mech

## arXiv C（Watch，需双条件）
("AI for science" | "LLM agent" | "agentic") AND (protein | "molecular dynamics" | "drug discovery" | "structural biology")

## bioRxiv 过滤（标题或摘要）
mechanosensitive | "ion channel" | "channel gating" | "membrane protein" | Piezo | MscL | "elastic network" | "normal mode" | allostery | allosteric | "protein dynamics" | "conformational ensemble" | "protein language model" | ESM-2 | ESM2 | ESMFold | ProteinMPNN | "inverse folding" | AlphaFold | "variant effect" | "mutation effect" | "deep mutational scanning" | "protein design"
注意：单独的 ESM 容易误中，只用 ESM-2/ESM2/ESMFold。

## PubMed 替代检索式（JCTC/JCIM/NSR 及通用）
力学/膜蛋白宽检索：("membrane protein"[tiab] OR mechanosensitive[tiab] OR "ion channel"[tiab] OR "elastic network"[tiab] OR "normal mode"[tiab] OR allostery[tiab] OR allosteric[tiab] OR "protein dynamics"[tiab])
交叉检索：上式 AND ("protein language model"[tiab] OR AlphaFold[tiab] OR ProteinMPNN[tiab] OR "inverse folding"[tiab] OR "mutation effect"[tiab] OR "variant effect"[tiab] OR "deep mutational scanning"[tiab] OR "molecular dynamics"[tiab] OR "protein design"[tiab])
按期刊限缩：加 "J Chem Theory Comput"[jour] / "J Mol Biol"[jour] / "J Chem Inf Model"[jour] / "Natl Sci Rev"[jour]
