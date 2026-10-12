import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  updatePassword,
  reauthenticateWithCredential,
  EmailAuthProvider,
  User,
} from "firebase/auth";
import {
  collection,
  doc,
  onSnapshot,
  query,
  where,
  documentId,
} from "firebase/firestore";
import {
  LayoutDashboard,
  Warehouse,
  Tags,
  Users,
  Upload,
  LogOut,
  ArrowUpRight,
  ArrowDownRight,
  Building2,
  Menu,
  KeyRound,
  Check,
  Plus,
  RefreshCw,
  Search,
  X,
  ChevronRight,
  LoaderCircle,
} from "lucide-react";
import { auth, db, call, loginEmail } from "./firebase";
import "./style.css";

type Row = Record<string, any>;

const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());

const monthOffset = (month: string, offset: number) => {
  const [year, value] = month.split("-").map(Number);
  const date = new Date(Date.UTC(year, value - 1 + offset, 1));
  return date.toISOString().slice(0, 7);
};

const roles: Row = {
  admin: "系統管理員",
  supervisor: "主管",
  manager: "店長",
  employee: "一般員工",
  pending: "待指派",
};

const types: Row = {
  new: "新承租",
  renew: "續約",
  exit: "退租",
};

const friendly = (error: any) => {
  const code = error?.code || "";
  if (/invalid-credential|user-not-found|wrong-password/.test(code))
    return "帳號或密碼不正確";
  if (code.includes("email-already-in-use"))
    return "此帳號已註冊";
  if (code.includes("too-many-requests"))
    return "登入嘗試過多，請稍後再試";
  if (code.includes("permission-denied"))
    return "沒有存取權限，請聯絡主管";
  if (code.includes("unavailable") || code.includes("internal"))
    return "服務暫時無法使用，請確認 Firebase 安全規則已部署或稍後再試";
  return error?.message || "操作失敗";
};

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Row | null>(null);
  const [loading, setLoading] = useState(true);
  const [branchRows, setBranches] = useState<Row[]>([]);
  const [branchId, setBranchId] = useState("all");
  const [page, setPage] = useState("dashboard");
  const [month, setMonth] = useState(today().slice(0, 7));
  const [data, setData] = useState<
    Record<string, {
      units: Row[];
      events: Row[];
      activities: Row[];
      months: Row[];
    }>
  >({});
  const [users, setUsers] = useState<Row[]>([]);
  const [modal, setModal] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [mobile, setMobile] = useState(false);

  const branches = [...branchRows].sort((a, b) =>
  String(a.name || "").localeCompare(
    String(b.name || ""),
    "zh-Hant-u-co-stroke",
    { numeric: true }
  )
);
  const global =
    profile && ["admin", "supervisor"].includes(profile.role);
  const canWrite =
    profile && ["admin", "supervisor", "manager"].includes(profile.role);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [page]);

  useEffect(() =>
    onAuthStateChanged(auth, (value) => {
      setUser(value);
      setProfile(null);
      setBranches([]);
      setData({});
      setBranchId("all");
      setLoading(false);
    }), []);

  useEffect(() => {
    if (!user) return;
    return onSnapshot(
      doc(db, "users", user.uid),
      (snapshot) =>
        setProfile(snapshot.exists() ? snapshot.data() : null),
      (error) => setError(friendly(error)),
    );
  }, [user]);

  useEffect(() => {
    if (!profile) return;
    const stops: (() => void)[] = [];
    const groups: Row[][] = [];

    if (global) {
      stops.push(onSnapshot(
        collection(db, "branches"),
        (snapshot) => setBranches(
          snapshot.docs.map((item) => ({
            id: item.id,
            ...item.data(),
          })),
        ),
        (error) => setError(friendly(error)),
      ));
      stops.push(onSnapshot(
        collection(db, "users"),
        (snapshot) => setUsers(
          snapshot.docs.map((item) => ({
            id: item.id,
            ...item.data(),
          })),
        ),
        (error) => setError(friendly(error)),
      ));
    } else {
      const ids = profile.branchIds || [];
      setBranches([]);
      for (let index = 0; index < ids.length; index += 30) {
        const group = index / 30;
        stops.push(onSnapshot(
          query(
            collection(db, "branches"),
            where(documentId(), "in", ids.slice(index, index + 30)),
          ),
          (snapshot) => {
            groups[group] = snapshot.docs.map((item) => ({
              id: item.id,
              ...item.data(),
            }));
            setBranches(groups.flat());
          },
          (error) => setError(friendly(error)),
        ));
      }
    }

    return () => stops.forEach((stop) => stop());
  }, [profile?.role, JSON.stringify(profile?.branchIds)]);

  useEffect(() => {
    setData({});
    const stops: (() => void)[] = [];
    if (page === "users") return;

    for (const branch of branches.filter(
      (item) =>
        !item.archived &&
        (branchId === "all" || item.id === branchId),
    )) {
      const sources: [string, any][] = [
        ["events", query(
          collection(db, "branches", branch.id, "events"),
          where("month", "==", month),
        )],
        ["activities", query(
          collection(db, "branches", branch.id, "activities"),
          where("month", "==", month),
        )],
        ["months", collection(db, "branches", branch.id, "months")],
      ];

      if (page === "units" || page === "imports") {
        sources.push([
          "units",
          collection(db, "branches", branch.id, "units"),
        ]);
      }

      for (const [name, source] of sources) {
        stops.push(onSnapshot(
          source,
          (snapshot: any) => setData((previous) => ({
            ...previous,
            [branch.id]: {
              ...(previous[branch.id] || {
                units: [],
                events: [],
                activities: [],
                months: [],
              }),
              [name]: snapshot.docs.map((item: any) => ({
                id: item.id,
                ...item.data(),
              })),
            },
          })),
          (error: any) => setError(friendly(error)),
        ));
      }
    }

    return () => stops.forEach((stop) => stop());
  }, [
    branches.map((branch) => branch.id).sort().join(","),
    branchId,
    page,
    month,
  ]);

  useEffect(() => {
    if (profile?.mustChangePassword) {
      setModal({ kind: "password", required: true });
    }
  }, [profile?.mustChangePassword]);

  const visible = branches.filter(
    (branch) =>
      !branch.archived &&
      (branchId === "all" || branch.id === branchId),
  );

  const units: Row[] = visible.flatMap((branch) =>
    (data[branch.id]?.units || []).map((unit) => ({
      ...unit,
      branchId: branch.id,
      branchName: branch.name,
    })),
  );

  const events: Row[] = visible.flatMap((branch) =>
    (data[branch.id]?.events || [])
      .filter((event) => !event.voided)
      .map((event) => ({
        ...event,
        branchId: branch.id,
        branchName: branch.name,
      })),
  );

  const activities: Row[] = visible.flatMap((branch) =>
    (data[branch.id]?.activities || []).map((activity) => ({
      ...activity,
      branchId: branch.id,
      branchName: branch.name,
    })),
  );

  const stats = (targetMonth: string) => {
    const isCurrent = targetMonth === today().slice(0, 7);
    const values = visible.map((branch) => {
      const saved = data[branch.id]?.months.find(
        (item) => item.id === targetMonth,
      );
      const tracked = isCurrent || saved?.source === "live";
      return {
        total:
          isCurrent && !branch.importing
            ? branch.total
            : saved?.total ?? null,
        rented:
          isCurrent && !branch.importing
            ? branch.rented
            : saved?.rented ?? null,
        new:
          saved?.source === "import"
            ? saved.new
            : tracked ? saved?.new || 0 : null,
        renew:
          saved?.source === "import"
            ? saved.renew
            : tracked ? saved?.renew || 0 : null,
        exit:
          saved?.source === "import"
            ? saved.exit
            : tracked ? saved?.exit || 0 : null,
      };
    });

    const sum = (key: string) =>
      values.length &&
      values.every((value) =>
        value[key as keyof typeof value] !== null,
      )
        ? values.reduce(
            (total, value) =>
              total + Number(value[key as keyof typeof value]),
            0,
          )
        : null;

    return {
      total: sum("total"),
      rented: sum("rented"),
      new: sum("new"),
      renew: sum("renew"),
      exit: sum("exit"),
    };
  };

  const current = stats(month);
  const previous = stats(monthOffset(month, -1));
  const lastYear = stats(monthOffset(month, -12));

  const rate = (value: ReturnType<typeof stats>) =>
    value.total && value.rented !== null
      ? value.rented / value.total * 100
      : null;

  const run = async (
    action: () => Promise<unknown>,
    message = "已儲存",
  ) => {
    setBusy(true);
    setError("");
    try {
      await action();
      setNotice(message);
      setModal(null);
    } catch (error) {
      setError(friendly(error));
    } finally {
      setBusy(false);
    }
  };

  const submit = (
    event: React.FormEvent<HTMLFormElement>,
    action: (form: Row) => Promise<unknown>,
    message?: string,
  ) => {
    event.preventDefault();
    const values = Object.fromEntries(
      new FormData(event.currentTarget),
    );
    run(() => action(values), message);
  };

  const changePassword = async (form: Row) => {
    if (form.password !== form.confirm)
      throw new Error("兩次新密碼不一致");
    if (String(form.password).length < 6)
      throw new Error("密碼至少六字元");
    if (!user?.email)
      throw new Error("請重新登入");

    await reauthenticateWithCredential(
      user,
      EmailAuthProvider.credential(user.email, form.old),
    );
    await updatePassword(user, form.password);
    await call("passwordChanged", {});
  };

  if (loading) {
    return (
      <div className="loading">
        <LoaderCircle className="spin" /> 正在載入…
      </div>
    );
  }

  if (!user) {
    return (
      <Login
        onError={setError}
        error={error}
        clearError={() => setError("")}
      />
    );
  }

  const tabs = [
    ["dashboard", "營運總覽", LayoutDashboard],
    ["units", "倉位管理", Warehouse],
    ["activities", "活動優惠", Tags],
    ["imports", "資料匯入", Upload],
    ...(global ? [["users", "帳號與權限", Users]] : []),
  ];

  return (
    <div className="app">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <div className="brand-icon">
            <Warehouse size={25} />
          </div>
          <div>
            收多易
            <span>STOREASY · 迷你倉庫</span>
          </div>
        </div>

        <div className="nav-caption">營運管理平台</div>

        <nav>
          {tabs.map(([id, label, Icon]: any) => (
            <button
              key={id}
              className={page === id ? "active" : ""}
              onClick={() => {
                setPage(id);
                setMobile(false);
                setSearch("");
              }}
            >
              <Icon size={19} />
              {label}
              {id === "users" &&
                users.some((item) => item.role === "pending") &&
                <i className="dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="avatar">
            {profile?.username?.slice(0, 1) || "S"}
          </div>
          <div>
            <strong>
              {profile?.username || user.displayName || "新帳號"}
            </strong>
            <span>
              {roles[profile?.role] || "註冊未完成"}
            </span>
          </div>
          <button title="登出" onClick={() => signOut(auth)}>
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      <main>
        <header>
          <div className="breadcrumb">
            <button
              className="mobile-toggle"
              onClick={() => setMobile(!mobile)}
            >
              <Menu />
            </button>
            工作空間 <ChevronRight size={14} />
            <strong>
              {tabs.find((tab) => tab[0] === page)?.[1] as string}
            </strong>
          </div>

          <div className="header-right">
            <span className="live-dot" /> 即時同步
            <span className="date">
              {today().replaceAll("-", " / ")}
            </span>
            <button
              title="更改密碼"
              onClick={() => setModal({ kind: "password" })}
            >
              <KeyRound size={18} />
            </button>
          </div>
        </header>

        <div className="content">
          {error && (
            <div role="alert" className="alert error">
              {error}
              <button onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}

          {notice && (
            <div role="status" className="alert success">
              {notice}
              <button onClick={() => setNotice("")}>
                <X size={16} />
              </button>
            </div>
          )}

          {!profile ? (
            <section className="panel empty">
              <Users size={40} />
              <h2>完成帳號註冊</h2>
              <p>
                登入已完成，請建立待指派資料，再由主管授予據點權限。
              </p>
              <form
                onSubmit={(event) =>
                  submit(event, (form) =>
                    call("registerProfile", {
                      username: form.username,
                    }),
                  )
                }
              >
                <label>
                  登入帳號
                  <input
                    name="username"
                    required
                    defaultValue={user.email?.split("@")[0]}
                  />
                </label>
                <button className="primary" disabled={busy}>
                  完成註冊
                </button>
              </form>
            </section>
          ) : profile.role === "pending" ? (
            <section className="panel empty">
              <Users size={48} />
              <h2>帳號已註冊，等待指派據點</h2>
              <p>
                主管指派角色及據點後，這裡會自動顯示你的營運資料。
              </p>
            </section>
          ) : (
            <>
              <div className="page-title">
                <div>
                  <div className="eyebrow">
                    STOREASY OPERATIONS
                  </div>
                  <h1>
                    {tabs.find((tab) =>
                      tab[0] === page,
                    )?.[1] as string}
                  </h1>
                  <p>
                    {page === "dashboard"
                      ? "掌握每個據點的出租表現，讓營運決策更清楚。"
                      : page === "units"
                        ? "管理倉位現況，記錄每一次承租、續約與退租。"
                        : page === "activities"
                          ? "各據點專屬優惠，使用成效一次掌握。"
                          : page === "imports"
                            ? "從 Excel 匯入倉位現況與歷史月度統計。"
                            : "管理註冊申請、角色與據點存取權限。"}
                  </p>
                </div>

                {page !== "users" && (
                  <div className="filters">
                    <select
                      aria-label="選擇據點"
                      value={branchId}
                      onChange={(event) =>
                        setBranchId(event.target.value)
                      }
                    >
                      <option value="all">
                        全部可查看據點
                      </option>
                      {branches
                        .filter((branch) => !branch.archived)
                        .map((branch) => (
                          <option
                            key={branch.id}
                            value={branch.id}
                          >
                            {branch.name}
                          </option>
                        ))}
                    </select>

                    <input
                      aria-label="統計月份"
                      type="month"
                      value={month}
                      max={today().slice(0, 7)}
                      onChange={(event) =>
                        setMonth(
                          event.target.value ||
                          today().slice(0, 7),
                        )
                      }
                    />
                  </div>
                )}
              </div>

              {visible.some((branch) =>
                branch.importing,
              ) && (
                <div className="alert error">
                  據點匯入中或上次匯入中斷，暫停異動與現況統計。
                  中斷時請十分鐘後重新提交完整檔案復原。
                </div>
              )}

              {page === "dashboard" && (
                <>
                  <div className="section-label">
                    <span>營運指標</span>
                    <span>
                      {month} · {visible.length} 個據點
                    </span>
                  </div>

                  <div className="cards">
                    {[
                      [
                        "總倉位",
                        current.total,
                        Warehouse,
                        "總可出租倉位",
                      ],
                      [
                        "已出租",
                        current.rented,
                        Check,
                        "目前使用中的倉位",
                      ],
                      [
                        "空置倉位",
                        current.total !== null &&
                        current.rented !== null
                          ? current.total - current.rented
                          : null,
                        Building2,
                        "可供承租的倉位",
                      ],
                      [
                        "出租率",
                        rate(current) !== null
                          ? `${rate(current)!.toFixed(1)}%`
                          : null,
                        ArrowUpRight,
                        "依倉位數量計算",
                      ],
                    ].map(
                      ([label, value, Icon, description]: any, index) => (
                        <div
                          className={`stat-card stat-${index}`}
                          key={label}
                        >
                          <div className="stat-top">
                            <span>{label}</span>
                            <Icon size={20} />
                          </div>
                          <strong>{value ?? "—"}</strong>
                          <small>{description}</small>
                        </div>
                      ),
                    )}
                  </div>

                  <div className="dashboard-grid">
                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <h2>出租率趨勢</h2>
                          <p>
                            最近六個月 · 每月最後紀錄／本月即時
                          </p>
                        </div>
                        <span className="legend">
                          <i /> 出租率
                        </span>
                      </div>

                      <div className="chart">
                        {Array.from(
                          { length: 6 },
                          (_, index) =>
                            monthOffset(month, index - 5),
                        ).map((value) => {
                          const percentage = rate(stats(value));
                          return (
                            <div
                              className="bar-column"
                              key={value}
                            >
                              <span>
                                {percentage === null
                                  ? "無資料"
                                  : `${percentage.toFixed(1)}%`}
                              </span>
                              <div className="bar-track">
                                <div
                                  className={
                                    value === month
                                      ? "bar highlight"
                                      : "bar"
                                  }
                                  style={{
                                    height:
                                      percentage === null
                                        ? "0%"
                                        : `${percentage}%`,
                                  }}
                                />
                              </div>
                              <small>
                                {value.slice(5)} 月
                              </small>
                            </div>
                          );
                        })}
                      </div>

                      <div className="comparisons">
                        {[
                          ["較上個月", previous],
                          ["較去年同月", lastYear],
                        ].map(([label, value]: any) => {
                          const currentRate = rate(current);
                          const previousRate = rate(value);
                          const difference =
                            currentRate !== null &&
                            previousRate !== null
                              ? currentRate - previousRate
                              : null;
                          return (
                            <div key={label}>
                              <span>{label}</span>
                              <strong
                                className={
                                  difference !== null &&
                                  difference < 0
                                    ? "negative"
                                    : "positive"
                                }
                              >
                                {difference === null
                                  ? "尚無資料"
                                  : `${difference >= 0 ? "+" : ""}${difference.toFixed(1)} 個百分點`}
                              </strong>
                            </div>
                          );
                        })}
                      </div>
                    </section>

                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <h2>本月承租動態</h2>
                          <p>{month} 的營運異動</p>
                        </div>
                        <RefreshCw size={20} />
                      </div>

                      <div className="flow-list">
                        {[
                          ["new", current.new],
                          ["renew", current.renew],
                          ["exit", current.exit],
                        ].map(([key, value]: any) => (
                          <div
                            className="flow-row"
                            key={key}
                          >
                            <div
                              className={`flow-icon ${key}`}
                            >
                              {key === "exit"
                                ? <ArrowDownRight />
                                : <ArrowUpRight />}
                            </div>
                            <span>{types[key]}</span>
                            <strong>
                              {value ?? "—"}
                              <small> 筆</small>
                            </strong>
                          </div>
                        ))}
                      </div>

                      <div className="soft-note">
                        首次盤點與重新匯入不計為承租異動。
                        歷史月份採匯入 KPI；缺少的資料顯示「—」。
                      </div>
                    </section>
                  </div>

                  <section className="panel">
                    <div className="panel-heading">
                      <div>
                        <h2>各據點營運概況</h2>
                        <p>即時倉位現況</p>
                      </div>
                      {global && (
                        <button
                          className="secondary"
                          onClick={() =>
                            setModal({ kind: "branch" })
                          }
                        >
                          <Plus size={16} />
                          新增據點
                        </button>
                      )}
                    </div>

                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>據點</th>
                            <th>總倉位</th>
                            <th>已出租</th>
                            <th>空置</th>
                            <th>出租率</th>
                            <th>資料日期</th>
                            {global && <th>管理</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {visible.map((branch) => (
                            <tr key={branch.id}>
                              <td>
                                <div className="branch-cell">
                                  <span className="branch-icon">
                                    <Building2 size={18} />
                                  </span>
                                  <strong>
                                    {branch.name}
                                  </strong>
                                </div>
                              </td>
                              <td>{branch.total}</td>
                              <td>{branch.rented}</td>
                              <td>{branch.vacant}</td>
                              <td>
                                <div className="rate-cell">
                                  <span>
                                    {branch.importing
                                      ? "匯入中"
                                      : branch.total
                                        ? `${(branch.rented / branch.total * 100).toFixed(1)}%`
                                        : "—"}
                                  </span>
                                  <div className="meter">
                                    <i style={{
                                      width: `${branch.total ? branch.rented / branch.total * 100 : 0}%`,
                                    }} />
                                  </div>
                                </div>
                              </td>
                              <td>
                                {branch.inventoryDate || "尚未匯入"}
                              </td>
                              {global && (
                                <td>
                                  <button
                                    className="text-button"
                                    onClick={() =>
                                      setModal({
                                        kind: "branch",
                                        ...branch,
                                      })
                                    }
                                  >
                                    修改名稱
                                  </button>
                                </td>
                              )}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {!visible.length && (
                        <Empty text="尚無據點，請主管新增據點並匯入資料。" />
                      )}
                    </div>
                  </section>

                  <section className="panel">
                    <div className="panel-heading">
                      <div>
                        <h2>活動使用概況</h2>
                        <p>
                          同筆承租可使用多個活動，
                          使用次數不等於承租筆數。
                        </p>
                      </div>
                    </div>

                    <div className="activity-summary">
                      {activities
                        .filter((activity) =>
                          activity.month === month,
                        )
                        .map((activity) => {
                          const count = events.filter(
                            (event) =>
                              event.month === month &&
                              event.branchId === activity.branchId &&
                              event.activities?.some(
                                (item: Row) =>
                                  item.id === activity.id,
                              ),
                          ).length;
                          return (
                            <div
                              key={activity.branchId + activity.id}
                            >
                              <span>
                                {activity.branchName} · {activity.name}
                              </span>
                              <strong>
                                {count}<small> 次</small>
                              </strong>
                            </div>
                          );
                        })}
                    </div>

                    {!activities.some(
                      (activity) => activity.month === month,
                    ) && <Empty text="本月尚無活動" />}
                  </section>
                </>
              )}

              {page === "units" && (
                <>
                  <div className="toolbar">
                    <div className="search">
                      <Search size={17} />
                      <input
                        placeholder="搜尋倉位編號或據點"
                        value={search}
                        onChange={(event) =>
                          setSearch(event.target.value)
                        }
                      />
                    </div>

                    <select
                      value={status}
                      onChange={(event) =>
                        setStatus(event.target.value)
                      }
                    >
                      <option value="all">全部狀態</option>
                      <option value="rented">已出租</option>
                      <option value="vacant">空倉</option>
                      <option value="missing">清單中消失</option>
                    </select>

                    {canWrite && (
                      <button
                        className="primary"
                        disabled={branchId === "all"}
                        onClick={() =>
                          setModal({
                            kind: "unitEdit",
                            branchId,
                          })
                        }
                      >
                        <Plus size={16} /> 新增倉位
                      </button>
                    )}
                  </div>

                  <section className="panel">
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>倉位／據點</th>
                            <th>尺寸</th>
                            <th>材積</th>
                            <th>月租</th>
                            <th>狀態</th>
                            <th>備註</th>
                            {canWrite && <th>操作</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {units
                            .filter((unit) =>
                              (
                                status === "all" ||
                                (status === "missing" && unit.missing) ||
                                (status === unit.status && !unit.missing)
                              ) &&
                              `${unit.code}${unit.branchName}`
                                .toLowerCase()
                                .includes(search.toLowerCase()),
                            )
                            .sort((a, b) =>
                              a.code.localeCompare(b.code),
                            )
                            .map((unit) => (
                              <tr
                                key={unit.branchId + unit.code}
                              >
                                <td>
                                  <strong>{unit.code}</strong>
                                  <small className="table-sub">
                                    {unit.branchName}
                                  </small>
                                </td>
                                <td>{unit.dimensions || "—"}</td>
                                <td>{unit.volume}</td>
                                <td>
                                  NT$ {Number(unit.price).toLocaleString()}
                                </td>
                                <td>
                                  <span className={`badge ${
                                    unit.missing
                                      ? "warning"
                                      : unit.status === "rented"
                                        ? "blue"
                                        : "green"
                                  }`}>
                                    {unit.missing
                                      ? "清單中消失"
                                      : unit.status === "rented"
                                        ? "已出租"
                                        : "空倉"}
                                  </span>
                                </td>
                                <td>{unit.note || "—"}</td>

                                {canWrite && (
                                  <td>
                                    <div className="row-actions">
                                      {!unit.missing && (
                                        <>
                                          <button
                                            className="text-button"
                                            onClick={() => {
                                              setMonth(today().slice(0, 7));
                                              setModal({
                                                kind: "event",
                                                unit,
                                                type:
                                                  unit.status === "vacant"
                                                    ? "new"
                                                    : "exit",
                                              });
                                            }}
                                          >
                                            {unit.status === "vacant"
                                              ? "承租"
                                              : "退租"}
                                          </button>

                                          {unit.status === "rented" && (
                                            <button
                                              className="text-button"
                                              onClick={() => {
                                                setMonth(today().slice(0, 7));
                                                setModal({
                                                  kind: "event",
                                                  unit,
                                                  type: "renew",
                                                });
                                              }}
                                            >
                                              續約
                                            </button>
                                          )}
                                        </>
                                      )}

                                      <button
                                        className="text-button"
                                        onClick={() =>
                                          setModal({
                                            kind: "unitEdit",
                                            ...unit,
                                          })
                                        }
                                      >
                                        編輯
                                      </button>
                                    </div>
                                  </td>
                                )}
                              </tr>
                            ))}
                        </tbody>
                      </table>
                      {!units.length && (
                        <Empty text="尚無倉位資料，請先匯入總倉與空倉清單。" />
                      )}
                    </div>
                  </section>

                  <section className="panel">
                    <div className="panel-heading">
                      <h2>異動紀錄 · {month}</h2>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>日期</th>
                            <th>倉位／據點</th>
                            <th>類型</th>
                            <th>異動當時牌價</th>
                            <th>使用活動</th>
                            {canWrite && <th>更正</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {events
                            .filter((event) => event.month === month)
                            .sort((a, b) =>
                              b.date.localeCompare(a.date),
                            )
                            .map((event) => (
                              <tr key={event.id}>
                                <td>{event.date}</td>
                                <td>
                                  {event.code}
                                  <small className="table-sub">
                                    {event.branchName}
                                  </small>
                                </td>
                                <td>{types[event.type]}</td>
                                <td>
                                  {event.priceSnapshot?.price === undefined
                                    ? "尚未記錄"
                                    : `NT$ ${Number(
                                        event.priceSnapshot.price
                                      ).toLocaleString()}`}
                                </td>
                                <td>
                                  {event.activities
                                    ?.map((activity: Row) => activity.name)
                                    .join("、") || "—"}
                                </td>
                                {canWrite && (
                                  <td>
                                    <button
                                      className="text-button"
                                      onClick={() =>
                                        setModal({
                                          kind: "void",
                                          event,
                                        })
                                      }
                                    >
                                      撤銷
                                    </button>
                                  </td>
                                )}
                              </tr>
                            ))}
                        </tbody>
                      </table>
                      {!events.some(
                        (event) => event.month === month,
                      ) && (
                        <Empty text="沒有逐筆異動紀錄；歷史 KPI 僅提供月度統計。" />
                      )}
                    </div>
                  </section>
                </>
              )}

              {page === "activities" && (
                <>
                  <div className="toolbar">
                    <span>
                      每間據點可建立自己的月度活動
                    </span>
                    {canWrite && (
                      <button
                        className="primary"
                        disabled={branchId === "all"}
                        onClick={() =>
                          setModal({
                            kind: "activity",
                            branchId,
                            month,
                          })
                        }
                      >
                        <Plus size={17} /> 新增活動
                      </button>
                    )}
                  </div>

                  {branchId === "all" && canWrite && (
                    <p className="hint">
                      請先選擇據點，再新增活動。
                    </p>
                  )}

                  <div className="activity-grid">
                    {activities
                      .filter((activity) =>
                        activity.month === month && !activity.archived,
                      )
                      .map((activity) => (
                        <section
                          className="panel activity-card"
                          key={activity.branchId + activity.id}
                        >
                          <span className="tag-icon">
                            <Tags size={22} />
                          </span>
                          <span className="badge blue">
                            {activity.branchName}
                          </span>
                          <h2>{activity.name}</h2>
                          <p>
                            {activity.description || "未填寫活動說明"}
                          </p>
                          <div className="activity-bottom">
                            <span>
                              {events.filter((event) =>
                                event.month === month &&
                                event.branchId === activity.branchId &&
                                event.activities?.some(
                                  (item: Row) =>
                                    item.id === activity.id,
                                ),
                              ).length} 次使用
                            </span>
                            {canWrite && (
                              <button
                                className="text-button"
                                onClick={() =>
                                  setModal({
                                    kind: "activity",
                                    ...activity,
                                  })
                                }
                              >
                                編輯活動
                              </button>
                            )}
                          </div>
                        </section>
                      ))}
                  </div>

                  {!activities.some(
                    (activity) =>
                      activity.month === month && !activity.archived,
                  ) && (
                    <section className="panel">
                      <Empty text="本月尚無活動" />
                    </section>
                  )}
                </>
              )}

              {page === "imports" && (
                <>
                  <div className="import-grid">
                    <section className="panel import-card">
                      <div className="upload-icon">
                        <Warehouse />
                      </div>
                      <h2>倉位現況匯入</h2>
                      <p>
                        同時選擇總倉與空倉 Excel。
                        總倉扣除空倉即為已出租，
                        匯入前先預覽比對結果。
                      </p>
                      <ul>
                        <li>
                          欄位：倉位、尺寸 W*L*H、材積、
                          單價、月租、備註
                        </li>
                        <li>
                          消失的倉位會標示保留，不直接刪除
                        </li>
                        <li>
                          盤點不計入新承租／退租業績
                        </li>
                      </ul>
                      {canWrite ? (
                        <button
                          className="primary"
                          disabled={branchId === "all"}
                          onClick={() =>
                            setModal({
                              kind: "inventory",
                              branchId,
                            })
                          }
                        >
                          <Upload size={17} />
                          選擇匯入檔案
                        </button>
                      ) : (
                        <p>
                          只有店長、主管及管理員可以匯入。
                        </p>
                      )}
                    </section>

                    <section className="panel import-card">
                      <div className="upload-icon yellow">
                        <LayoutDashboard />
                      </div>
                      <h2>歷史 KPI 匯入</h2>
                      <p>
                        讀取各年度工作表與月度指標，
                        供上月和去年同月比較使用。
                      </p>
                      <ul>
                        <li>
                          新承租採「新約數量（不含轉倉）」
                        </li>
                        <li>
                          續約加總月租、季繳、半年及年約
                        </li>
                        <li>
                          只匯入已結算月份，
                          不覆蓋即時操作紀錄
                        </li>
                      </ul>
                      {canWrite && (
                        <button
                          className="secondary"
                          disabled={branchId === "all"}
                          onClick={() =>
                            setModal({
                              kind: "kpi",
                              branchId,
                            })
                          }
                        >
                          <Upload size={17} />
                          匯入歷史 KPI
                        </button>
                      )}
                    </section>
                  </div>

                  {branchId === "all" && (
                    <p className="hint">
                      請先在右上角選擇一個據點。
                    </p>
                  )}

                  <section className="panel">
                    <div className="panel-heading">
                      <h2>歷史統計資料</h2>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>據點／月份</th>
                            <th>總倉位</th>
                            <th>已出租</th>
                            <th>新承租</th>
                            <th>續約</th>
                            <th>退租</th>
                            {canWrite && <th>操作</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {visible.flatMap((branch) =>
                            (data[branch.id]?.months || [])
                              .filter((item) => item.source === "import")
                              .map((item) => (
                                <tr key={branch.id + item.id}>
                                  <td>
                                    {branch.name}
                                    <small className="table-sub">
                                      {item.id}
                                    </small>
                                  </td>
                                  {[
                                    "total",
                                    "rented",
                                    "new",
                                    "renew",
                                    "exit",
                                  ].map((key) => (
                                    <td key={key}>
                                      {item[key] ?? "—"}
                                    </td>
                                  ))}
                                  {canWrite && (
                                    <td>
                                      <button
                                        className="text-button danger"
                                        onClick={() =>
                                          setModal({
                                            kind: "removeKpi",
                                            branchId: branch.id,
                                            month: item.id,
                                          })
                                        }
                                      >
                                        移除
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              )),
                          )}
                        </tbody>
                      </table>
                    </div>
                  </section>
                </>
              )}

              {page === "users" && global && (
                <>
                  <div className="toolbar">
                    <div className="hint">
                      新註冊帳號：
                      {users.filter(
                        (item) => item.role === "pending",
                      ).length} 位待指派
                    </div>
                    <button
                      className="primary"
                      onClick={() =>
                        setModal({ kind: "createUser" })
                      }
                    >
                      <Plus size={16} />
                      協助建立帳號
                    </button>
                  </div>

                  <section className="panel">
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>帳號</th>
                            <th>角色</th>
                            <th>可查看據點</th>
                            <th>操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          {users
                            .sort((a, b) =>
                              (a.role === "pending" ? -1 : 1) -
                              (b.role === "pending" ? -1 : 1),
                            )
                            .map((item) => (
                              <tr key={item.id}>
                                <td>
                                  <strong>{item.username}</strong>
                                </td>
                                <td>
                                  <span className={`badge ${
                                    item.role === "pending"
                                      ? "warning"
                                      : "blue"
                                  }`}>
                                    {roles[item.role]}
                                  </span>
                                </td>
                                <td>
                                  {["admin", "supervisor"].includes(item.role)
                                    ? "全部據點"
                                    : item.branchIds
                                      ?.map((id: string) =>
                                        branches.find(
                                          (branch) => branch.id === id,
                                        )?.name || id,
                                      )
                                      .join("、") || "尚未指派"}
                                </td>
                                <td>
                                  <button
                                    className="text-button"
                                    disabled={
                                      item.id === user.uid ||
                                      (
                                        profile.role !== "admin" &&
                                        ["admin", "supervisor"]
                                          .includes(item.role)
                                      )
                                    }
                                    onClick={() =>
                                      setModal({
                                        kind: "assign",
                                        ...item,
                                      })
                                    }
                                  >
                                    指派權限
                                  </button>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                </>
              )}
            </>
          )}

          <footer>
            收多易迷你倉庫 · 營運管理平台
            <span>資料權限依帳號與據點限制</span>
          </footer>
        </div>
      </main>

      {modal && (
        <div className="modal-backdrop">
          <section
            role="dialog"
            aria-modal="true"
            className={`modal ${
              ["inventory", "kpi"].includes(modal.kind)
                ? "wide"
                : ""
            }`}
          >
            <div className="modal-heading">
              <h2>
                {({
                  password: "更改密碼",
                  branch: "據點資料",
                  event: `登記${types[modal.type]}`,
                  activity: "活動設定",
                  inventory: "匯入倉位現況",
                  kpi: "匯入歷史 KPI",
                  assign: "指派角色與據點",
                  createUser: "建立帳號",
                  unitEdit: "倉位資料",
                  void: "撤銷異動",
                  removeKpi: "移除歷史統計",
                  deleteUnit: "刪除倉位",
                } as Row)[modal.kind]}
              </h2>

              {!modal.required && (
                <button
                  disabled={busy}
                  aria-label="關閉"
                  onClick={() => setModal(null)}
                >
                  <X />
                </button>
              )}
            </div>

            {error && (
              <div className="alert error" role="alert">
                {error}
              </div>
            )}

            {modal.kind === "password" && (
              <form
                onSubmit={(event) =>
                  submit(
                    event,
                    changePassword,
                    "密碼已更新",
                  )
                }
              >
                <p>
                  {modal.required
                    ? "初次登入，請先更改初始密碼。"
                    : "請輸入目前密碼，以確認身分。"}
                </p>
                <label>
                  目前密碼
                  <input
                    type="password"
                    name="old"
                    required
                    autoComplete="current-password"
                  />
                </label>
                <label>
                  新密碼
                  <input
                    type="password"
                    name="password"
                    minLength={6}
                    required
                    autoComplete="new-password"
                  />
                </label>
                <label>
                  再次輸入新密碼
                  <input
                    type="password"
                    name="confirm"
                    minLength={6}
                    required
                    autoComplete="new-password"
                  />
                </label>
                <Submit busy={busy} />
              </form>
            )}

            {modal.kind === "branch" && (
              <form
                onSubmit={(event) =>
                  submit(event, (form) =>
                    call("saveBranch", {
                      id: modal.id,
                      name: form.name,
                    }),
                  )
                }
              >
                <label>
                  據點名稱
                  <input
                    name="name"
                    required
                    maxLength={80}
                    defaultValue={modal.name}
                  />
                </label>
                <Submit busy={busy} />
              </form>
            )}

            {modal.kind === "event" && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  const form = new FormData(event.currentTarget);
                  run(
                    () => call("recordEvent", {
                      branchId: modal.unit.branchId,
                      code: modal.unit.code,
                      type: modal.type,
                      date: form.get("date"),
                      activityIds: form.getAll("activity"),
                    }),
                    "倉位狀態與異動已更新",
                  );
                }}
              >
                <p>
                  <strong>{modal.unit.code}</strong>
                  {" "}· {modal.unit.branchName}
                </p>
                <label>
                  異動日期
                  <input
                    type="date"
                    name="date"
                    defaultValue={today()}
                    max={today()}
                    required
                    onChange={(event) => {
                      setMonth(
                        event.target.value.slice(0, 7) ||
                        today().slice(0, 7),
                      );
                      setModal({
                        ...modal,
                        eventMonth:
                          event.target.value.slice(0, 7),
                      });
                    }}
                  />
                </label>

                {modal.type !== "exit" && (
                  <fieldset>
                    <legend>使用活動（可複選）</legend>
                    {activities
                      .filter((activity) =>
                        activity.branchId === modal.unit.branchId &&
                        activity.month ===
                          (modal.eventMonth || today().slice(0, 7)) &&
                        !activity.archived,
                      )
                      .map((activity) => (
                        <label
                          className="check-label"
                          key={activity.id}
                        >
                          <input
                            type="checkbox"
                            name="activity"
                            value={activity.id}
                          />
                          {activity.name}
                        </label>
                      ))}
                  </fieldset>
                )}

                <p className="hint">
                  歷史 KPI 已結算的月份不能新增異動。
                </p>
                <Submit busy={busy} />
              </form>
            )}

            {modal.kind === "activity" && (
              <form
                onSubmit={(event) =>
                  submit(event, (form) =>
                    call("saveActivity", {
                      ...form,
                      id: modal.id,
                      branchId: modal.branchId,
                    }),
                  )
                }
              >
                <label>
                  活動月份
                  <input
                    name="month"
                    type="month"
                    required
                    defaultValue={modal.month}
                  />
                </label>
                <label>
                  活動名稱
                  <input
                    name="name"
                    required
                    maxLength={100}
                    defaultValue={modal.name}
                  />
                </label>
                <label>
                  活動說明
                  <textarea
                    name="description"
                    maxLength={1000}
                    defaultValue={modal.description}
                  />
                </label>
                <Submit busy={busy} />

                {modal.id && (
                  <button
                    className="danger secondary"
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      run(
                        () => call("saveActivity", {
                          ...modal,
                          remove: true,
                        }),
                        "活動已停用，既有使用紀錄保留",
                      )
                    }
                  >
                    停用活動
                  </button>
                )}
              </form>
            )}

            {["inventory", "kpi"].includes(modal.kind) && (
              <ImportForm
                kind={modal.kind}
                branchId={modal.branchId}
                busy={busy}
                units={data[modal.branchId]?.units || []}
                onSubmit={(payload: Row) =>
                  run(
                    () => call(
                      modal.kind === "inventory"
                        ? "importInventory"
                        : "importKpi",
                      {
                        branchId: modal.branchId,
                        ...payload,
                      },
                    ),
                    "資料匯入完成",
                  )
                }
                onError={setError}
              />
            )}

            {modal.kind === "assign" && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  const form = new FormData(event.currentTarget);
                  run(
                    () => call("manageUser", {
                      action: "assign",
                      uid: modal.id,
                      role: form.get("role"),
                      branchIds: form.getAll("branch"),
                    }),
                    "權限已更新",
                  );
                }}
              >
                <p>
                  帳號：<strong>{modal.username}</strong>
                </p>

                <label>
                  角色
                  <select
                    aria-label="角色"
                    name="role"
                    defaultValue={modal.role}
                  >
                    {Object.entries(roles)
                      .filter(([key]) =>
                        profile?.role === "admin" ||
                        !["admin", "supervisor"].includes(key),
                      )
                      .map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                  </select>
                </label>

                <fieldset>
                  <legend>
                    指派據點（店長與員工適用）
                  </legend>
                  {branches.map((branch) => (
                    <label
                      className="check-label"
                      key={branch.id}
                    >
                      <input
                        name="branch"
                        type="checkbox"
                        value={branch.id}
                        defaultChecked={
                          modal.branchIds?.includes(branch.id)
                        }
                      />
                      {branch.name}
                    </label>
                  ))}
                </fieldset>

                <Submit busy={busy} />
              </form>
            )}

            {modal.kind === "createUser" && (
              <form
                onSubmit={(event) =>
                  submit(
                    event,
                    (form) => call("manageUser", {
                      action: "create",
                      ...form,
                    }),
                    "帳號已建立，請再指派權限",
                  )
                }
              >
                <label>
                  登入帳號
                  <input
                    name="username"
                    pattern="[a-zA-Z0-9_-]{2,32}"
                    required
                  />
                </label>
                <label>
                  初始密碼
                  <input
                    name="password"
                    type="password"
                    minLength={6}
                    required
                    autoComplete="new-password"
                  />
                </label>
                <p className="hint">
                  新帳號預設待指派，
                  首次登入須更改密碼。
                </p>
                <Submit busy={busy} />
              </form>
            )}

            {modal.kind === "unitEdit" && (
              <form
                onSubmit={(event) =>
                  submit(event, (form) =>
                    call("saveUnit", {
                      ...form,
                      branchId: modal.branchId,
                      code: modal.code || form.code,
                    }),
                  )
                }
              >
                <label>
                  倉位編號
                  <input
                    name="code"
                    defaultValue={modal.code}
                    readOnly={!!modal.code}
                    required
                  />
                </label>
                <label>
                  尺寸
                  <input
                    name="dimensions"
                    defaultValue={modal.dimensions}
                  />
                </label>

                <div className="form-grid">
                  <label>
                    材積
                    <input
                      type="number"
                      step="any"
                      min="0"
                      name="volume"
                      defaultValue={modal.volume || 0}
                    />
                  </label>
                  <label>
                    月租
                    <input
                      type="number"
                      step="any"
                      min="0"
                      name="price"
                      defaultValue={modal.price || 0}
                    />
                  </label>
                </div>

                <label>
                  單價
                  <input
                    type="number"
                    step="any"
                    min="0"
                    name="unitPrice"
                    defaultValue={modal.unitPrice || 0}
                  />
                </label>
                <label>
                  備註
                  <textarea
                    name="note"
                    defaultValue={modal.note}
                  />
                </label>

                <Submit busy={busy} />

                {modal.code && (
                  <button
                    type="button"
                    className="secondary danger"
                    disabled={
                      busy || modal.status === "rented"
                    }
                    onClick={() =>
                      setModal({
                        ...modal,
                        kind: "deleteUnit",
                      })
                    }
                  >
                    刪除空倉
                  </button>
                )}
              </form>
            )}

            {modal.kind === "void" && (
              <>
                <p>
                  撤銷 {modal.event.code} 在
                  {" "}{modal.event.date} 的
                  {types[modal.event.type]}？
                  僅能撤銷該倉位最後一筆異動，
                  恢復先前狀態。
                </p>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    run(
                      () => call("voidEvent", {
                        branchId: modal.event.branchId,
                        eventId: modal.event.id,
                      }),
                      "異動已撤銷",
                    )
                  }
                >
                  確認撤銷
                </button>
              </>
            )}

            {modal.kind === "deleteUnit" && (
              <>
                <p>
                  確定刪除空倉 {modal.code}？
                  既有異動紀錄仍保留。
                </p>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    run(
                      () => call("saveUnit", {
                        branchId: modal.branchId,
                        code: modal.code,
                        remove: true,
                      }),
                      "倉位已刪除",
                    )
                  }
                >
                  確認刪除
                </button>
              </>
            )}

            {modal.kind === "removeKpi" && (
              <>
                <p>
                  移除 {modal.month} 的匯入統計？
                  該月份將不再提供歷史比較。
                </p>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    run(
                      () => call("importKpi", {
                        branchId: modal.branchId,
                        removeMonth: modal.month,
                      }),
                      "歷史統計已移除",
                    )
                  }
                >
                  確認移除
                </button>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function Submit({ busy }: { busy: boolean }) {
  return (
    <button
      className="primary submit"
      disabled={busy}
    >
      {busy ? (
        <>
          <LoaderCircle className="spin" size={16} />
          處理中…
        </>
      ) : "確認儲存"}
    </button>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="empty">
      <Warehouse size={28} />
      <p>{text}</p>
    </div>
  );
}

function Login({
  error,
  onError,
  clearError,
}: {
  error: string;
  onError: (message: string) => void;
  clearError: () => void;
}) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);

  return (
    <div className="login-page">
      <div className="login-story">
        <div className="brand">
          <div className="brand-icon">
            <Warehouse />
          </div>
          <div>
            收多易
            <span>STOREASY · 迷你倉庫</span>
          </div>
        </div>

        <span className="eyebrow">
          SPACE FOR BETTER DECISIONS
        </span>
        <h1>
          每一個空間，
          <br />
          都看得更清楚。
        </h1>
        <p>
          串起各據點的營運現況，
          <br />
          讓承租、續約與活動成效一目了然。
        </p>

        <div className="warehouse-art">
          <div /><div /><div />
          <div /><div /><div />
        </div>
        <small>
          收多易迷你倉庫 · 營運管理平台
        </small>
      </div>

      <section className="login-form">
        <div className="login-mark">
          <Warehouse size={28} />
        </div>
        <h2>
          {register ? "建立你的帳號" : "歡迎回來"}
        </h2>
        <p>
          {register
            ? "註冊後由主管指派角色與據點。"
            : "登入以查看你的據點營運資訊。"}
        </p>

        {error && (
          <div role="alert" className="alert error">
            {error}
          </div>
        )}

        <form
          onSubmit={async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            setBusy(true);
            clearError();

            try {
              const username = String(form.get("username"));
              const email = loginEmail(username);

              if (register) {
                if (
                  form.get("password") !== form.get("confirm")
                ) {
                  throw new Error("兩次密碼不一致");
                }

                await createUserWithEmailAndPassword(
                  auth,
                  email,
                  String(form.get("password")),
                );
                await call("registerProfile", { username });
              } else {
                await signInWithEmailAndPassword(
                  auth,
                  email,
                  String(form.get("password")),
                );
              }
            } catch (error) {
              onError(friendly(error));
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            帳號
            <input
              name="username"
              required
              pattern="[a-zA-Z0-9_-]{2,32}"
              autoComplete="username"
              placeholder="輸入你的帳號"
            />
          </label>

          <label>
            密碼
            <input
              name="password"
              type="password"
              minLength={6}
              required
              autoComplete={
                register
                  ? "new-password"
                  : "current-password"
              }
              placeholder="至少 6 個字元"
            />
          </label>

          {register && (
            <label>
              確認密碼
              <input
                name="confirm"
                type="password"
                minLength={6}
                required
                autoComplete="new-password"
              />
            </label>
          )}

          <button
            className="primary submit"
            disabled={busy}
          >
            {busy
              ? "處理中…"
              : register
                ? "註冊帳號"
                : "登入平台"}
            <ArrowUpRight size={18} />
          </button>
        </form>

        <div className="login-switch">
          {register
            ? "已經有帳號？"
            : "還沒有帳號？"}
          <button
            className="text-button"
            onClick={() => {
              setRegister(!register);
              clearError();
            }}
          >
            {register ? "返回登入" : "自行註冊"}
          </button>
        </div>

        <small className="hint">
          忘記密碼請聯絡管理員。帳號不分大小寫。
        </small>
      </section>
    </div>
  );
}

function ImportForm({
  kind,
  branchId,
  busy,
  units,
  onSubmit,
  onError,
}: {
  kind: string;
  branchId: string;
  busy: boolean;
  units: Row[];
  onSubmit: (payload: Row) => void;
  onError: (message: string) => void;
}) {
  const [preview, setPreview] = useState<Row | null>(null);
  const [reading, setReading] = useState(false);

  return (
    <>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          setReading(true);
          onError("");

          try {
            const {
              workbook,
              parseUnits,
              parseKpi,
            } = await import("./imports");

            if (kind === "inventory") {
              const all = parseUnits(
                await workbook(
                  await (form.get("all") as File).arrayBuffer(),
                ),
              );
              const vacant = parseUnits(
                await workbook(
                  await (form.get("vacant") as File).arrayBuffer(),
                ),
                undefined,
                { requirePrice: false },
              ).map((unit: Row) => unit.code);
              const codes = new Set(
                all.map((unit: Row) => unit.code),
              );

              if (
                vacant.some(
                  (code: string) => !codes.has(code),
                )
              ) {
                throw new Error(
                  "空倉表含總倉清單不存在的倉位",
                );
              }

              setPreview({
                units: all,
                vacantCodes: vacant,
                effectiveDate: form.get("date"),
                missing: units
                  .filter((unit) => !codes.has(unit.code))
                  .map((unit) => unit.code),
              });
            } else {
              const months = parseKpi(
                await workbook(
                  await (form.get("kpi") as File).arrayBuffer(),
                ),
              );

              setPreview({
                months: months.filter(
                  (item: Row) =>
                    item.month < today().slice(0, 7),
                ),
                excluded: months.filter(
                  (item: Row) =>
                    item.month >= today().slice(0, 7),
                ).length,
              });
            }
          } catch (error) {
            onError(friendly(error));
          } finally {
            setReading(false);
          }
        }}
      >
        {kind === "inventory" ? (
          <>
            <label>
              總倉 Excel
              <input
                name="all"
                type="file"
                accept=".xlsx"
                required
                onChange={() => setPreview(null)}
              />
            </label>
            <label>
              空倉 Excel
              <input
                name="vacant"
                type="file"
                accept=".xlsx"
                required
                onChange={() => setPreview(null)}
              />
            </label>
            <label>
              盤點生效日期
              <input
                name="date"
                type="date"
                defaultValue={today()}
                max={today()}
                required
                onChange={() => setPreview(null)}
              />
            </label>
          </>
        ) : (
          <label>
            歷史 KPI Excel
            <input
              name="kpi"
              type="file"
              accept=".xlsx"
              required
              onChange={() => setPreview(null)}
            />
          </label>
        )}

        <button
          className="secondary"
          disabled={busy || reading}
        >
          {reading ? "讀取中…" : "分析並預覽"}
        </button>
      </form>

      {preview && (
        <div className="import-preview">
          {kind === "inventory" ? (
            <>
              <h3>匯入比對結果</h3>
              <div className="preview-counts">
                <span>
                  總倉 <b>{preview.units.length}</b>
                </span>
                <span>
                  空倉 <b>{preview.vacantCodes.length}</b>
                </span>
                <span>
                  已出租{" "}
                  <b>
                    {preview.units.length -
                      preview.vacantCodes.length}
                  </b>
                </span>
              </div>

              {preview.missing.length > 0 && (
                <div className="alert error">
                  清單中消失：
                  {preview.missing.join("、")}。
                  保留並標示，暫不計入出租率。
                </div>
              )}

              <p className="hint">
                此操作會依檔案更新現況，
                不計入新承租／退租。
                逐筆紀錄仍會保留。
              </p>
            </>
          ) : (
            <>
              <h3>
                已結算月份：{preview.months.length} 筆
              </h3>
              <p className="hint">
                排除本月及未來月份 {preview.excluded} 筆。
                缺少的續約或承租數量保留為無資料。
              </p>
              <div className="table-wrap preview-table">
                <table>
                  <thead>
                    <tr>
                      <th>月份</th>
                      <th>總倉</th>
                      <th>已出租</th>
                      <th>新承租</th>
                      <th>續約</th>
                      <th>退租</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.months.map((item: Row) => (
                      <tr key={item.month}>
                        <td>{item.month}</td>
                        {[
                          "total",
                          "rented",
                          "new",
                          "renew",
                          "exit",
                        ].map((key) => (
                          <td key={key}>
                            {item[key] ?? "—"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          <button
            className="primary submit"
            disabled={
              busy ||
              (kind === "kpi" && !preview.months.length)
            }
            onClick={() => onSubmit(preview)}
          >
            {busy ? "正在匯入…" : "確認匯入"}
          </button>
        </div>
      )}
    </>
  );
}

createRoot(
  document.getElementById("root")!,
).render(<App />);
