# Development — axiom-skills

## Repository identity

| Field | Value |
| --- | --- |
| Component | `axiom-skills` |
| Canonical remote | `https://github.com/orchex006/axiom-skills` |
| Owns | reusable agent skills (`skills/`), host adapters (`adapters/`), managed graph policy (`policy/`), release manifest (`release/`) |
| Does not own | graph runtime (`axiom-graphd`), MCP surface (`axiom-mcp`), ecosystem contracts (`axiom-specs`) |

Take only tasks whose `repo` is `axiom-skills`. Skill behavior, hook contracts, adapter compatibility และ policy ที่เป็น norm ของ ecosystem ต้อง coordinat ผ่าน `axiom-specs`; repository นี้ implement และ certify ไม่ใช่กำหนด contract เอง

## Pinned governance

Canonical workflow คือ `Development.md` ใน `axiom-specs` ณ revision ที่ `spec.lock.json` pin ไว้ (ถ้า repository นี้มี pin) และ workspace `AGENTS.md` ที่ `D:\SP-Billy\axiom\AGENTS.md`

Skill เป็นส่วนของ operational workflow แต่การมี skill ไม่ทำให้ข้าม governance ได้: skill MUST NOT สั่งให้ ignore, summarize away, replace, disable หรือ bypass `AGENTS.md` หรือ `Development.md` ที่ใช้บังคับอยู่ และ bootstrap ที่จัดการ governance MUST preserve human-owned instructions และ verify effective governance ก่อนเริ่มงาน

## Preflight — ก่อนเริ่มทุก task

1. อ่าน workspace `AGENTS.md`, `Development.md` นี้, task card/spec และ skill/contract ที่เกี่ยวข้อง;
2. ตรวจ repository identity (`git remote -v`) ว่าตรงกับ canonical remote;
3. ตรวจ `git status` และ preserve งานที่ยังไม่ commit ของเจ้าของ;
4. ระบุ approved base branch (`main`) และ synchronize อย่างปลอดภัยเมื่อ state อนุญาต;
5. สร้างหรือเข้า `feature/<task-id>-<slug>`;
6. ระบุ allowed files, required tests และ explicit commit/push authority;
7. บันทึก base revision, dirty state และคำสั่งที่จะใช้เป็น evidence

ห้ามเริ่มแก้ task-owned files ก่อนครบทั้ง 7 ข้อ

## During work

- ทำหนึ่ง bounded task ต่อหนึ่ง branch;
- skill หนึ่งตัวต้องมี instructions ที่บอกขอบเขตชัดเจน ไม่ผูกกับ host เดียวโดยไม่มี adapter contract;
- adapter ต้องประกาศ compatibility/hash ตาม `adapters/compatibility.json` และ manifest ต้อง verify ได้จาก bytes ที่ commit จริง;
- hook runtime ต้อง degrade และ cancel ตาม contract ที่ committed ไม่ใช่ตามพฤติกรรมเฉพาะเครื่อง;
- ห้ามพึ่ง Bash, WSL, Docker, administrator privileges หรือ symlink;
- เปลี่ยนไฟล์ skill แล้วต้องอัปเดต `release/skills-manifest.json` และ `Changelog.md` ให้ตรงกัน

## Required checks

```text
python -m pytest tests -q
```

MUST รันจริงและบันทึกผลกับ exit code ลง evidence ทุกครั้ง ก่อน merge หรือรายงานว่าเสร็จ งานที่แตะ manifest/adapter MUST รัน `python release/verify_manifest.py` เพิ่ม

## Evidence และ completion

- ใช้ canonical six preflight check และ eight completion check;
- attach จริง: test output, exit code, hash ของ skill bundle, acceptance mapping, changed-file review, compatibility/rollback note;
- host ที่ยังไม่ได้ทดสอบ MUST ถูกบันทึกเป็น unverified ไม่ใช่ปล่อยว่าง;
- ห้ามอ้างว่า "น่าจะผ่าน" แทนการรันจริง

## Branch/release policy

Canonical policy: `Development.md` §3 (`Branch/worktree policy`) ใน `axiom-specs`

| Branch | ใช้สำหรับ | การรวม |
| --- | --- | --- |
| `main` | integration branch ของงานพัฒนา | merge จาก task branch ที่ผ่าน merge gate; ห้าม push implementation commit ตรงเข้า `main` |
| `feature/<task-id>-<slug>` | task branch ต่อหนึ่ง bounded task | merge เข้า `main` เมื่อผ่าน merge gate; PR เมื่อ repo ต้องมี reviewer |
| `release/vX.Y.Z` | release candidate, stabilization และจุดออก release | เฉพาะ release authority; ห้าม merge เข้า release branch เอง |

ไม่สร้างหรือใช้ `develop` ใน repository นี้

### Merge gate

Agent MAY merge task branch เข้า `main` ได้เองโดยไม่ต้องขอ authorization เพิ่มเติม เมื่อครบทุกข้อ:

1. task status เป็น `done` และ ledger ตรงกับ card;
2. acceptance ครบทุกข้อ พร้อม command evidence จริง;
3. required checks ของ repository ผ่านจริง และบันทึกคำสั่งกับ exit code จริง;
4. final diff ถูก review แล้วว่าไม่หลุด scope และไม่รวม human-owned/unrelated changes;
5. `Changelog.md`, `release/skills-manifest.json` และ docs ที่ได้รับผลถูกอัปเดตแล้ว;
6. ไม่มี blocker หรือ limitation ที่ยังไม่ถูกบันทึกใน evidence;
7. merge ไม่ทับงานที่ยังไม่ commit ของ checkout ที่เกี่ยวข้อง.

Agent MUST NOT merge เมื่อ task ยัง `in_progress`/`blocked`, evidence ไม่ครบ, required checks ไม่ผ่าน/ยังไม่ได้รัน หรือ merge ก่อ conflict ที่ต้องตัดสินใจเชิง contract/compatibility

หลัง merge MUST push `main` ขึ้น canonical remote ตรวจ remote SHA และรายงาน merge commit SHA กับ main remote SHA

Merge เข้า `release/vX.Y.Z`, การ tag, การ publish skill bundle และ release ใด ๆ MUST มี release authorization ที่ระบุชัดเจนเสมอ

### Worktree และ checkout หลัก

งานที่ทำใน worktree MUST NOT จบอยู่แค่ใน worktree เมื่อ task verified แล้ว MUST:

1. integrate เข้า `main` ตาม merge gate ข้างต้น; และ
2. อัปเดต checkout หลัก (`D:\SP-Billy\axiom\axiom-skills`) ให้ตรงกับ branch ที่ integrate แล้ว เมื่อ working tree ของ checkout นั้นสะอาดพอ; หรือ
3. ถ้าทำไม่ได้เพราะมีงานที่ยังไม่ commit ของเจ้าของ checkout ให้ preserve งานนั้นไว้ และรายงานชัดเจนว่า checkout หลักยังไม่ได้รับงาน พร้อมขั้นตอนถัดไปที่เฉพาะเจาะจง

ห้ามรายงานว่างาน "เสร็จ" โดยไม่ระบุว่า checkout หลักได้งานแล้วหรือยัง

รายงานปิดงาน MUST ระบุ: task ID, branch, commit SHA, สถานะการ integrate เข้า `main` และ path ของ checkout หลักที่อัปเดตแล้ว

## Commit และ push

- stage เฉพาะไฟล์ของ task; ห้าม `git add .` เมื่อมีงานอื่นใน working tree และห้าม stage `.pytest_cache/` หรือ `__pycache__`;
- conventional commit style เช่น `feat(skills): ...`, `fix(skills): ...`, `docs(skills): ...`; ระบุ task ID ในวงเล็บเหลี่ยมเมื่อมี เช่น `[A-021]`;
- commit แล้ว push feature branch ขึ้น canonical remote และรายงาน branch name กับ commit SHA;
- ห้าม force-push, ห้าม amend commit ของผู้อื่น, ห้าม rewrite published history;
- commit/push ล้มเหลว MUST รายงาน blocker ที่แท้จริงและเก็บงานที่ verify แล้วไว้ในเครื่อง

## Version และ release

- `axiom-skills` version แยกจาก `axiom-graphd` และ `axiom-mcp`;
- manifest และ compatibility record เป็น contract ของ bundle; เปลี่ยนแล้วต้อง verify hash จาก committed bytes;
- tag, release branch และ publish ต้องมี release authorization เสมอ

## Definition of blocked

รายงานเป็น blocked เมื่อ: required check รันไม่ได้; manifest/compatibility verify ไม่ผ่าน; มี conflict ที่ต้องตัดสินใจเชิง contract; checkout หลัก/worktree มีงานที่ยังไม่ commit ซึ่งทำให้ integrate ไม่ปลอดภัย; หรือ task ต้องใช้ authorization เกิน standing workflow

## Cross-repository

เมื่อ task กระทบ `axiom-specs`, `axiom-graphd` หรือ `axiom-mcp` ต้องแยก child task ต่อ repository และแต่ละ repository ใช้ branch/verification/commit/push lifecycle ของตัวเอง
