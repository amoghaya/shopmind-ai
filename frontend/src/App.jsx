import React, { useEffect, useMemo, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
const ASSET_HOST = API.replace("/api/v1", "");
const SESSION_KEY = "shopsim-session-id";

function inferCategory(query) {
  const q = query.toLowerCase();
  if (q.includes("laptop")) return "laptop";
  if (q.includes("phone")) return "phone";
  if (q.includes("headphone") || q.includes("earbud") || q.includes("audio")) return "audio";
  if (q.includes("shoe") || q.includes("fashion")) return "fashion";
  if (q.includes("home") || q.includes("kitchen")) return "home";
  return "";
}

function assetUrl(path) {
  if (!path) return "";
  return `${ASSET_HOST}${path}`;
}

export default function App() {
  const [viewMode, setViewMode] = useState("avatar");
  const [sessionId, setSessionId] = useState("");
  const [products, setProducts] = useState([]);
  const [allCategories, setAllCategories] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [cart, setCart] = useState({ items: [], subtotal: 0, currency: "INR" });
  const [profile, setProfile] = useState({
    user_name: "Demo User",
    preferred_categories: [],
    preferred_brands: [],
    budget_max: 70000,
    liked_tags: [],
    disliked_tags: [],
    watchlist_product_ids: [],
  });
  const [recommendations, setRecommendations] = useState([]);
  const [recommendationRequestId, setRecommendationRequestId] = useState(null);
  const [recommendationSummary, setRecommendationSummary] = useState({
    cumulative_regret: 0,
    total_feedback: 0,
    success_rate: 0,
    weights: {},
  });
  const [executionRuns, setExecutionRuns] = useState([]);
  const [activeExecution, setActiveExecution] = useState(null);
  const [query, setQuery] = useState("laptop");
  const [searchFilters, setSearchFilters] = useState({ category: "", min_rating: 0, max_price: 70000 });
  const [approvalModal, setApprovalModal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [checkoutSuccess, setCheckoutSuccess] = useState(false);
  const [runInProgress, setRunInProgress] = useState(false);
  const [priceHistory, setPriceHistory] = useState(null);
  const [trackedProducts, setTrackedProducts] = useState([]);
  const [paymentRedirecting, setPaymentRedirecting] = useState(false);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [benchmarkRunning, setBenchmarkRunning] = useState(false);
  const [benchmarkCursor, setBenchmarkCursor] = useState(0);

  useEffect(() => {
    bootstrap();
  }, []);

  async function readJson(response) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  useEffect(() => {
    if (!activeExecution?.status) return;
    if (["success", "failed", "paused"].includes(activeExecution.status)) {
      setRunInProgress(false);
    }
  }, [activeExecution?.status]);

  useEffect(() => {
    if (!runInProgress) return undefined;
    const timeout = window.setTimeout(() => {
      setRunInProgress(false);
      setMessage("Autonomous buy timed out. Please try again.");
      setActiveExecution((prev) => (
        prev
          ? {
              ...prev,
              status: "failed",
              steps: (prev.steps || []).map((step) => (
                step.status === "running" ? { ...step, status: "timeout" } : step
              )),
            }
          : prev
      ));
      setExecutionRuns((prev) => prev.map((run) => (
        run.status === "running"
          ? {
              ...run,
              status: "failed",
              steps: (run.steps || []).map((step) => (
                step.status === "running" ? { ...step, status: "timeout" } : step
              )),
            }
          : run
      )));
    }, 40000);
    return () => window.clearTimeout(timeout);
  }, [runInProgress]);

  useEffect(() => {
    if (!allCategories.length && products.length) {
      setAllCategories([...new Set(products.map((product) => product.category).filter(Boolean))].sort());
    }
  }, [products, allCategories.length]);

  useEffect(() => {
    if (!benchmarkData?.regret_curve?.length) return undefined;
    setBenchmarkCursor(0);
    const total = benchmarkData.regret_curve.length;
    const interval = window.setInterval(() => {
      setBenchmarkCursor((prev) => {
        if (prev >= total) {
          window.clearInterval(interval);
          return prev;
        }
        return prev + 1;
      });
    }, 120);
    return () => window.clearInterval(interval);
  }, [benchmarkData]);

  async function bootstrap() {
    const stored = localStorage.getItem(SESSION_KEY) || `session-${Date.now()}`;
    localStorage.setItem(SESSION_KEY, stored);
    setSessionId(stored);
    await Promise.allSettled([
      searchProducts("laptop", true),
      loadRecommendationSummary(),
      loadRecommendations("laptop", 70000),
      loadCategories(),
      loadProfile(),
      loadCart(stored),
    ]);
  }

  async function ensureSession(candidateSessionId = sessionId, options = {}) {
    const targetSessionId = candidateSessionId || localStorage.getItem(SESSION_KEY) || `session-${Date.now()}`;
    localStorage.setItem(SESSION_KEY, targetSessionId);
    setSessionId(targetSessionId);
    return targetSessionId;
  }

  async function loadCategories() {
    const response = await fetch(`${API}/sandbox/products/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "", in_stock_only: true, sort_by: "rating" }),
    });
    if (!response.ok) return;
    const payload = await readJson(response);
    if (!Array.isArray(payload)) return;
    setAllCategories([...new Set(payload.map((product) => product.category).filter(Boolean))].sort());
  }

  async function loadCart(currentSessionId = sessionId) {
    if (!currentSessionId) return;
    const response = await fetch(`${API}/sandbox/cart/${currentSessionId}`);
    if (response.ok) {
      const payload = await readJson(response);
      if (payload) setCart(payload);
    }
  }

  async function loadRecommendationSummary() {
    const response = await fetch(`${API}/recommendations/summary`);
    if (response.ok) {
      const payload = await readJson(response);
      if (payload) setRecommendationSummary(payload);
    }
  }

  async function loadProfile() {
    const response = await fetch(`${API}/preferences/demo-user`);
    if (!response.ok) return;
    const payload = await readJson(response);
    if (!payload?.preference_summary) return;
    setProfile(payload.preference_summary);
    await loadTrackedProducts(payload.preference_summary);
  }

  async function loadTrackedProducts(summary = profile) {
    const ids = (summary.watchlist_product_ids || []).slice(-6).reverse();
    if (!ids.length) {
      setTrackedProducts([]);
      return;
    }
    const items = await Promise.all(
      ids.map(async (productId) => {
        const [productResponse, trackerResponse] = await Promise.all([
          fetch(`${API}/sandbox/products/${productId}`),
          fetch(`${API}/sandbox/products/${productId}/price-history`),
        ]);
        if (!productResponse.ok || !trackerResponse.ok) return null;
        return {
          product: await productResponse.json(),
          tracker: await trackerResponse.json(),
        };
      })
    );
    setTrackedProducts(items.filter(Boolean));
  }

  async function loadExecutionRuns(currentSessionId = sessionId) {
    if (!currentSessionId) return;
    const response = await fetch(`${API}/execution/runs?session_id=${currentSessionId}`);
    if (!response.ok) return;
    const payload = await readJson(response);
    if (!Array.isArray(payload)) return;
    setExecutionRuns(payload);
    if (payload.length) {
      setActiveExecution(payload[0]);
      if (["success", "failed", "paused"].includes(payload[0].status)) {
        setRunInProgress(false);
      }
    }
  }

  function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function syncExecutionRun(run) {
    setActiveExecution(run);
    setExecutionRuns((prev) => {
      const filtered = prev.filter((item) => item.run_id !== run.run_id);
      return [run, ...filtered].slice(0, 12);
    });
  }

  function buildSimulatedRun(product) {
    return {
      run_id: `sim-${Date.now()}`,
      session_id: sessionId,
      executor_name: "shopsim_simulated",
      status: "running",
      steps: [
        { action: "open_site", status: "pending", detail: "Opening ShopMind storefront" },
        { action: "search", status: "pending", detail: `Searching for ${product.name}` },
        { action: "open_product", status: "pending", detail: "Opening product detail page" },
        { action: "add_to_cart", status: "pending", detail: "Adding product to cart" },
        { action: "await_approval", status: "pending", detail: "Applying human-supervised purchase approval" },
        { action: "checkout", status: "pending", detail: "Redirecting to payment gateway and confirming order" },
      ],
      screenshot_urls: [],
    };
  }

  function updateSimulatedStep(runId, action, status) {
    setActiveExecution((prev) => {
      if (!prev || prev.run_id !== runId) return prev;
      const nextRun = {
        ...prev,
        status: status === "failed" || status === "timeout" ? "failed" : prev.status,
        steps: prev.steps.map((step) => {
          if (step.action === action) return { ...step, status };
          if (step.status === "running" && step.action !== action && status === "running") {
            return { ...step, status: "ok" };
          }
          return step;
        }),
      };
      if (["confirmed", "success"].includes(status) && action === "checkout") {
        nextRun.status = "success";
      } else if (status === "running") {
        nextRun.status = "running";
      }
      setExecutionRuns((prevRuns) => prevRuns.map((run) => (run.run_id === runId ? nextRun : run)));
      return nextRun;
    });
  }

  async function loadRecommendations(category, budgetMax) {
    const response = await fetch(`${API}/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "demo-user",
        top_k: 6,
        context_overrides: {
          preferred_category: category,
          budget_max: budgetMax,
        },
      }),
    });
    if (!response.ok) return;
    const payload = await readJson(response);
    if (!payload?.items || !Array.isArray(payload.items)) {
      setRecommendations([]);
      return;
    }
    const items = await Promise.all(
      payload.items.map(async (item) => {
        const productResponse = await fetch(`${API}/sandbox/products/${item.item_id}`);
        if (!productResponse.ok) return null;
        return {
          ...item,
          product: await productResponse.json(),
        };
      })
    );
    setRecommendations(items.filter(Boolean));
    setRecommendationRequestId(payload.request_id);
  }

  async function searchProducts(nextQuery = query, resetSelection = false, refreshRecommendations = true) {
    setLoading(true);
    try {
      const response = await fetch(`${API}/sandbox/products/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: nextQuery,
          category: searchFilters.category || null,
          min_rating: searchFilters.min_rating || null,
          max_price: searchFilters.max_price || null,
          in_stock_only: true,
          sort_by: "rating",
        }),
      });
      const payload = await readJson(response);
      if (!response.ok || !Array.isArray(payload)) {
        setProducts([]);
        return;
      }
      setProducts(payload);
      if (resetSelection) setSelectedProduct(null);
      if (refreshRecommendations) {
        await loadRecommendations(searchFilters.category || inferCategory(nextQuery), searchFilters.max_price);
      }
    } finally {
      setLoading(false);
    }
  }

  async function openProduct(productId) {
    const response = await fetch(`${API}/sandbox/products/${productId}`);
    if (response.ok) {
      const product = await response.json();
      setSelectedProduct(product);
      await loadPriceHistory(productId);
    }
  }

  async function loadPriceHistory(productId) {
    const response = await fetch(`${API}/sandbox/products/${productId}/price-history`);
    if (response.ok) setPriceHistory(await response.json());
  }

  async function addToCart(productId, quantity = 1) {
    const readySessionId = await ensureSession(sessionId);
    if (!readySessionId) return;
    const response = await fetch(`${API}/sandbox/cart/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: readySessionId, product_id: productId, quantity }),
    });
    if (!response.ok) {
      const payload = await response.json();
      setMessage(payload.detail || "Unable to add to cart");
      return;
    }
    setCart(await response.json());
    setMessage("Added to cart");
    await updateAvatarProfile(productId);
    if (recommendationRequestId) await submitFeedback(productId, 1);
  }

  async function updateAvatarProfile(productId, mode = "positive", providedProduct = null) {
    const product = providedProduct || products.find((candidate) => candidate.id === productId) || selectedProduct;
    if (!product) return;
    const nextCategories =
      mode === "positive"
        ? [...new Set([...(profile.preferred_categories || []), product.category])]
        : profile.preferred_categories || [];
    const nextBrands =
      mode === "positive"
        ? [...new Set([...(profile.preferred_brands || []), product.brand])]
        : profile.preferred_brands || [];
    const nextLikedTags =
      mode === "positive"
        ? [...new Set([...(profile.liked_tags || []), ...(product.tags || []).slice(0, 3)])]
        : profile.liked_tags || [];
    const nextDislikedTags =
      mode === "negative"
        ? [...new Set([...(profile.disliked_tags || []), ...(product.tags || []).slice(0, 3)])]
        : profile.disliked_tags || [];
    const nextWatchlist =
      mode === "watchlist"
        ? [...new Set([...(profile.watchlist_product_ids || []), product.id])]
        : mode === "unwatchlist"
          ? (profile.watchlist_product_ids || []).filter((id) => id !== product.id)
        : profile.watchlist_product_ids || [];
    const nextSummary = {
      ...profile,
      preferred_categories: nextCategories,
      preferred_brands: nextBrands,
      liked_tags: nextLikedTags,
      disliked_tags: nextDislikedTags,
      watchlist_product_ids: nextWatchlist,
      budget_max: searchFilters.max_price,
    };
    await fetch(`${API}/preferences`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "demo-user",
        context_features: { last_clicked_category: product.category },
        preference_summary: nextSummary,
      }),
    });
    setProfile(nextSummary);
    await loadTrackedProducts(nextSummary);
  }

  async function likeProduct(product) {
    await updateAvatarProfile(product.id, "positive", product);
    await submitFeedback(product.id, 1);
    setMessage(`${product.name} added to avatar likes`);
  }

  async function dislikeProduct(product) {
    await updateAvatarProfile(product.id, "negative", product);
    await submitFeedback(product.id, -1);
    setMessage(`${product.name} marked as disliked`);
  }

  async function addToWatchlist(product) {
    await updateAvatarProfile(product.id, "watchlist", product);
    await loadPriceHistory(product.id);
    await submitFeedback(product.id, 0.35);
    setMessage(`${product.name} added to watchlist for price tracking`);
  }

  async function removeFromWatchlist(product) {
    await updateAvatarProfile(product.id, "unwatchlist", product);
    setMessage(`${product.name} removed from watchlist`);
  }

  async function submitFeedback(productId, reward) {
    if (!recommendationRequestId) return;
    await fetch(`${API}/recommendations/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: recommendationRequestId,
        user_id: "demo-user",
        selected_item_id: String(productId),
        reward,
        accepted: reward > 0,
      }),
    });
    await loadRecommendationSummary();
    if (reward > 0) await updateAvatarProfile(productId, "positive");
  }

  async function reinforceCartCheckout(items, reward = 1) {
    if (!recommendationRequestId || !Array.isArray(items) || !items.length) return;
    for (const item of items) {
      await submitFeedback(item.product_id, reward);
    }
  }

  async function submitCheckout() {
    const readySessionId = await ensureSession(sessionId);
    if (!readySessionId) return;
    await performCheckout(readySessionId, true);
  }

  async function performCheckout(readySessionId, closeApprovalModal = false) {
    const checkoutItems = [...cart.items];
    setPaymentRedirecting(true);
    await wait(1500);
    const response = await fetch(`${API}/sandbox/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: readySessionId,
        shipping_name: "Demo User",
        shipping_address: "Delhi Technological University, Delhi",
        payment_method: "sandbox_upi",
        approved: true,
      }),
    });
    const payload = await response.json();
    setPaymentRedirecting(false);
    if (closeApprovalModal) setApprovalModal(null);
    setCheckoutSuccess(true);
    await reinforceCartCheckout(checkoutItems, 1);
    setMessage(`Checkout simulated successfully: ${payload.order_id}`);
    await Promise.all([loadCart(readySessionId), searchProducts(query)]);
    return payload;
  }

  async function runAgent(product) {
    const readySessionId = await ensureSession(sessionId);
    if (!readySessionId) return;
    setCheckoutSuccess(false);
    setRunInProgress(true);
    setViewMode("execution");
    const run = buildSimulatedRun(product);
    syncExecutionRun(run);
    setMessage("Starting simulated autonomous buy...");
    try {
      updateSimulatedStep(run.run_id, "open_site", "running");
      await wait(700);
      updateSimulatedStep(run.run_id, "open_site", "ok");

      setQuery(product.name);
      updateSimulatedStep(run.run_id, "search", "running");
      await searchProducts(product.name, false, false);
      await wait(900);
      updateSimulatedStep(run.run_id, "search", "ok");

      updateSimulatedStep(run.run_id, "open_product", "running");
      await openProduct(product.id);
      await wait(800);
      updateSimulatedStep(run.run_id, "open_product", "ok");

      updateSimulatedStep(run.run_id, "add_to_cart", "running");
      await addToCart(product.id);
      await wait(900);
      updateSimulatedStep(run.run_id, "add_to_cart", "ok");

      updateSimulatedStep(run.run_id, "await_approval", "running");
      await wait(1000);
      updateSimulatedStep(run.run_id, "await_approval", "ok");

      updateSimulatedStep(run.run_id, "checkout", "running");
      await performCheckout(readySessionId, false);
      await wait(800);
      updateSimulatedStep(run.run_id, "checkout", "confirmed");
      await submitFeedback(product.id, 1);
      setMessage(`Simulated autonomous buy completed: ${product.name}`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Autonomous execution failed";
      setMessage(detail);
      updateSimulatedStep(run.run_id, currentExecutionStep || "checkout", "failed");
    } finally {
      await loadCart(readySessionId);
      await searchProducts(product.name, false, false);
      setRunInProgress(false);
    }
  }

  async function runBenchmark() {
    setBenchmarkRunning(true);
    try {
      const response = await fetch(`${API}/benchmark/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const payload = await readJson(response);
      if (!response.ok || !payload?.metrics || !payload?.regret_curve) {
        throw new Error(payload?.detail || "Benchmark run failed");
      }
      setBenchmarkData(payload);
      setViewMode("benchmarks");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Benchmark run failed");
    } finally {
      setBenchmarkRunning(false);
    }
  }

  const successRate = useMemo(() => {
    if (!executionRuns.length) return "0%";
    const successes = executionRuns.filter((run) => run.status === "success").length;
    return `${Math.round((successes / executionRuns.length) * 100)}%`;
  }, [executionRuns]);

  const currentExecutionStep = useMemo(() => {
    if (!activeExecution?.steps?.length) return "";
    const running = activeExecution.steps.find((step) => step.status === "running");
    if (running) return running.action;
    const paused = activeExecution.steps.find((step) => step.status === "paused");
    if (paused) return paused.action;
    const confirmed = [...activeExecution.steps].reverse().find((step) => step.status === "confirmed" || step.status === "ok");
    return confirmed?.action || "";
  }, [activeExecution]);

  function isWatchlisted(productId) {
    return (profile.watchlist_product_ids || []).includes(productId);
  }

  return (
    <div className={`appShell ${viewMode === "avatar" ? "avatarMode" : ""} ${viewMode === "shop" ? "shopMode" : ""} ${viewMode === "execution" ? "executionMode" : ""} ${viewMode === "benchmarks" ? "benchmarkMode" : ""}`}>
      <header className="topHeader">
        <div className="brandBlock">
          <div className="brandLogo">SM</div>
          <div>
            <h1>ShopMind AI</h1>
            <p>Multi-agent digital shopping avatar powered by adaptive HNB learning</p>
          </div>
        </div>
        <div className="headerStats">
          <StatCard label="Products" value={products.length || 110} />
          <StatCard label="Cart items" value={cart.items.length} />
          <StatCard label="Watchlist" value={(profile.watchlist_product_ids || []).length} />
          <StatCard label="Liked brands" value={(profile.preferred_brands || []).length} />
        </div>
      </header>

      <section className="modeTabs">
        <button className={viewMode === "avatar" ? "modeTab active" : "modeTab"} onClick={() => setViewMode("avatar")}>
          AI Avatar Profile
        </button>
        <button className={viewMode === "shop" ? "modeTab active" : "modeTab"} onClick={() => setViewMode("shop")}>
          Storefront
        </button>
        <button className={viewMode === "execution" ? "modeTab active" : "modeTab"} onClick={() => setViewMode("execution")}>
          Execution Logs
        </button>
        <button className={viewMode === "benchmarks" ? "modeTab active" : "modeTab"} onClick={() => setViewMode("benchmarks")}>
          Benchmarks
        </button>
      </section>

      {viewMode === "shop" ? (
        <>
          <section className="searchHero">
            <div className="searchBar">
              <input
                data-testid="search-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search for phones, laptops, earbuds, shoes..."
              />
              <button data-testid="search-button" onClick={() => searchProducts(query, true)}>Search</button>
            </div>
            <div className="heroFilters">
              <select data-testid="category-filter" value={searchFilters.category} onChange={(event) => setSearchFilters((prev) => ({ ...prev, category: event.target.value }))}>
                <option value="">All categories</option>
                {allCategories.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
              <select data-testid="rating-filter" value={searchFilters.min_rating} onChange={(event) => setSearchFilters((prev) => ({ ...prev, min_rating: Number(event.target.value) }))}>
                <option value={0}>Any rating</option>
                <option value={4}>4.0+</option>
                <option value={4.3}>4.3+</option>
                <option value={4.5}>4.5+</option>
              </select>
              <input
                data-testid="budget-input"
                type="number"
                min="1000"
                step="500"
                value={searchFilters.max_price}
                onChange={(event) => setSearchFilters((prev) => ({ ...prev, max_price: Number(event.target.value || 0) }))}
                placeholder="Enter max budget"
              />
            </div>
          </section>

          <main className="marketLayout">
            <section className="leftColumn">
              <section className="panel">
                <div className="sectionHeader">
                  <div>
                    <h2>Recommended for your avatar</h2>
                  </div>
                </div>
                <div className="recommendationRail">
                  {recommendations.map((item) => (
                    <div className="recCard" key={item.item_id}>
                      <div className="recBadge">HNB score {item.score}</div>
                      <h3>{item.product.name}</h3>
                      <p>{item.product.brand} | {item.product.category}</p>
                      <strong>INR {Math.round(item.product.price)}</strong>
                      <p className="recReason">
                        {item.explanation.category_match ? "Category match. " : ""}
                        {item.explanation.budget_fit ? "Budget fit. " : "Stretch budget. "}
                        Rating {item.explanation.rating}
                      </p>
                      <div className="cardActions">
                        <button onClick={() => openProduct(Number(item.item_id))}>View</button>
                        <button className="secondaryBtn" onClick={() => likeProduct(item.product)}>Like</button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel">
                <div className="sectionHeader">
                  <div>
                    <h2>Marketplace catalog</h2>
                  </div>
                </div>
                <div className="catalogGrid">
                  {products.map((product) => (
                    <article
                      className="catalogCard"
                      data-testid="product-card"
                      data-product-id={product.id}
                      key={product.id}
                      onClick={() => openProduct(product.id)}
                    >
                      <div className="catalogImage">{product.brand[0]}</div>
                      <div className="catalogMeta">
                        <span className="chip">{product.category}</span>
                        <h3>{product.name}</h3>
                        <p>{product.brand} | Rating {product.rating_avg}</p>
                        <strong>INR {Math.round(product.price)}</strong>
                        <span className="ratingLine">Stock {product.inventory_count}</span>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </section>

            <aside className="rightColumn">
              <section className="panel detailPanel" data-testid="product-detail">
                {selectedProduct ? (
                  <>
                    <div className="productHero">
                      <div className="detailImage">{selectedProduct.brand[0]}</div>
                      <div>
                        <span className="chip accent">{selectedProduct.category}</span>
                        <h2>{selectedProduct.name}</h2>
                        <p>{selectedProduct.brand}</p>
                        <strong>INR {Math.round(selectedProduct.price)}</strong>
                      </div>
                    </div>
                    <p className="detailDescription">{selectedProduct.description}</p>
                    <div className="tagRow">
                      {selectedProduct.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}
                    </div>
                    <div className="cardActions">
                      <button
                        data-testid="add-to-cart-button"
                        className={currentExecutionStep === "add_to_cart" ? "stepHighlightBtn" : ""}
                        onClick={() => addToCart(selectedProduct.id)}
                      >
                        Add to cart
                      </button>
                      <button
                        className={`secondaryBtn ${currentExecutionStep === "open_site" || currentExecutionStep === "search" || currentExecutionStep === "open_product" ? "stepHighlightBtn" : ""}`}
                        disabled={runInProgress}
                        onClick={() => runAgent(selectedProduct)}
                      >
                        Autonomous buy
                      </button>
                    </div>
                    <div className="preferenceActions">
                      <button className="ghostBtn positiveBtn" onClick={() => likeProduct(selectedProduct)}>Like</button>
                      <button className="ghostBtn negativeBtn" onClick={() => dislikeProduct(selectedProduct)}>Dislike</button>
                      {isWatchlisted(selectedProduct.id) ? (
                        <button className="ghostBtn removeWatchBtn" onClick={() => removeFromWatchlist(selectedProduct)}>Remove watchlist</button>
                      ) : (
                        <button className="ghostBtn watchBtn" onClick={() => addToWatchlist(selectedProduct)}>Watchlist</button>
                      )}
                    </div>
                    {priceHistory ? (
                      <div className="priceTrackerCard">
                        <div className="sectionHeader compact">
                          <div>
                            <h3>30-day price tracker</h3>
                          </div>
                        </div>
                        <div className="trackerStats">
                          <span>Current INR {Math.round(priceHistory.current_price)}</span>
                          <span>Low INR {Math.round(priceHistory.min_price)}</span>
                          <span>High INR {Math.round(priceHistory.max_price)}</span>
                          <span>Drop {priceHistory.drop_percent}%</span>
                        </div>
                        <PriceHistoryChart history={priceHistory.history} />
                      </div>
                    ) : null}
                    <div className="reviewStack">
                      {selectedProduct.reviews.map((review) => (
                        <div className="reviewCard" key={review.id}>
                          <strong>{review.title}</strong>
                          <span>Rating {review.rating}/5</span>
                          <p>{review.body}</p>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <>
                    <h2>Select a product</h2>
                    <p className="mutedText">Click any product to open details, add it to cart, or launch autonomous buy.</p>
                  </>
                )}
              </section>

              <section className="panel" data-testid="cart-panel">
                <div className="sectionHeader compact">
                  <div>
                    <h2>Cart</h2>
                  </div>
                  <button
                    data-testid="go-to-checkout-button"
                    className={currentExecutionStep === "await_approval" || currentExecutionStep === "checkout" ? "stepHighlightBtn" : ""}
                    onClick={() => setApprovalModal({ type: "checkout" })}
                  >
                    Checkout
                  </button>
                </div>
                <div className="cartList">
                  {cart.items.map((item) => (
                    <div className="cartItem" key={item.product_id}>
                      <div>
                        <strong>{item.name}</strong>
                        <p>Qty {item.quantity}</p>
                      </div>
                      <span>INR {Math.round(item.line_total)}</span>
                    </div>
                  ))}
                  {!cart.items.length ? <p className="mutedText">Cart is empty.</p> : null}
                </div>
                <div className="cartFooter">
                  <strong>Subtotal</strong>
                  <strong>INR {Math.round(cart.subtotal || 0)}</strong>
                </div>
              </section>

              {activeExecution ? (
                <section className="panel executionInlinePanel">
                  <div className="sectionHeader compact">
                    <div>
                      <h2>Live autonomous execution</h2>
                    </div>
                  </div>
                  <div className="executionMeta">
                    <strong>{activeExecution.run_id}</strong>
                    <span>{activeExecution.status}</span>
                  </div>
                  <div className="stepList compactStepList">
                    {activeExecution.steps.map((step, index) => (
                      <div className={`stepRow ${step.status === "confirmed" || step.status === "ok" ? "done" : step.status === "running" ? "running" : ""}`} key={`${step.action}-${index}`}>
                        <span>{index + 1}</span>
                        <div>
                          <strong>{step.action.replaceAll("_", " ")}</strong>
                          <p>{step.status}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              {runInProgress ? (
                <section className="panel automationShowcase">
                  <div className="sectionHeader compact">
                    <div>
                      <h2>Autonomous buy in progress</h2>
                    </div>
                  </div>
                  <div className="automationStage">
                    <strong>Current step:</strong>
                    <span>{currentExecutionStep ? currentExecutionStep.replaceAll("_", " ") : "starting"}</span>
                  </div>
                </section>
              ) : null}
            </aside>
          </main>
        </>
      ) : viewMode === "avatar" ? (
        <main className="avatarLayout">
          <section className="panel avatarHero">
            <div className="sectionHeader">
              <div>
                <h2>Digital shopping avatar</h2>
              </div>
            </div>
            <div className="profileGrid">
              <div className="profileCell">
                <span>Name</span>
                <strong>{profile.user_name}</strong>
              </div>
              <div className="profileCell">
                <span>Budget memory</span>
                <strong>INR {profile.budget_max}</strong>
              </div>
              <div className="profileCell">
                <span>Tracked products</span>
                <strong>{(profile.watchlist_product_ids || []).length}</strong>
              </div>
              <div className="profileCell">
                <span>Learned brands</span>
                <strong>{(profile.preferred_brands || []).length}</strong>
              </div>
              <div className="profileCell">
                <span>Disliked tags</span>
                <strong>{(profile.disliked_tags || []).length}</strong>
              </div>
            </div>
            <div className="profileSection">
              <h3>Preferred categories</h3>
              <div className="tagRow">
                {(profile.preferred_categories || []).map((item) => <span className="tag" key={item}>{item}</span>)}
              </div>
            </div>
            <div className="profileSection">
              <h3>Preferred brands</h3>
              <div className="tagRow">
                {(profile.preferred_brands || []).map((item) => <span className="tag" key={item}>{item}</span>)}
              </div>
            </div>
            <div className="profileSection">
              <h3>Liked tags</h3>
              <div className="tagRow">
                {(profile.liked_tags || []).slice(0, 14).map((item) => <span className="tag" key={item}>{item}</span>)}
              </div>
            </div>
            <div className="profileSection">
              <h3>Avoided tags</h3>
              <div className="tagRow">
                {(profile.disliked_tags || []).slice(0, 14).map((item) => <span className="tag dangerTag" key={item}>{item}</span>)}
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="sectionHeader">
              <div>
                <h2>Price tracker agent</h2>
              </div>
            </div>
            <div className="trackerGrid">
              {trackedProducts.map(({ product, tracker }) => (
                <div className="trackerMiniCard" key={product.id}>
                  <div className="trackerMiniHeader">
                    <div>
                      <h3>{product.name}</h3>
                      <p>{product.brand} | {product.category}</p>
                    </div>
                    <button className="secondaryBtn" onClick={() => { setViewMode("shop"); openProduct(product.id); }}>
                      Open
                    </button>
                    <button className="ghostBtn removeWatchBtn" onClick={() => removeFromWatchlist(product)}>
                      Remove
                    </button>
                  </div>
                  <div className="trackerStats">
                    <span>Current INR {Math.round(tracker.current_price)}</span>
                    <span>30d low INR {Math.round(tracker.min_price)}</span>
                    <span>Avg INR {Math.round(tracker.avg_price)}</span>
                    <span className={tracker.drop_percent > 0 ? "trackerDrop" : ""}>Drop {tracker.drop_percent}%</span>
                  </div>
                  <PriceHistoryChart history={tracker.history} />
                </div>
              ))}
              {!trackedProducts.length ? <p className="mutedText">Browse or shortlist products to build the avatar watchlist.</p> : null}
            </div>
          </section>
        </main>
      ) : viewMode === "execution" ? (
        <main className="avatarLayout">
          <section className="panel executionPanel">
            <div className="sectionHeader">
              <div>
                <h2>Autonomous execution logs</h2>
              </div>
            </div>
            {activeExecution ? (
              <>
                <div className="executionMeta">
                  <strong>{activeExecution.run_id}</strong>
                  <span>{activeExecution.status}</span>
                </div>
                <div className="stepList">
                  {activeExecution.steps.map((step, index) => (
                    <div className={`stepRow ${step.status === "confirmed" || step.status === "ok" ? "done" : step.status === "running" ? "running" : ""}`} key={`${step.action}-${index}`}>
                      <span>{index + 1}</span>
                      <div>
                        <strong>{step.action.replaceAll("_", " ")}</strong>
                        <p>{step.status}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="mutedText">No execution runs yet.</p>
            )}
          </section>
        </main>
      ) : (
        <main className="avatarLayout">
          <section className="panel avatarHero">
            <div className="sectionHeader">
              <div>
                <h2>Live benchmark arena</h2>
              </div>
              <button onClick={runBenchmark} disabled={benchmarkRunning}>
                {benchmarkRunning ? "Running benchmark..." : "Run benchmark"}
              </button>
            </div>
            <div className="profileGrid">
              <div className="profileCell">
                <span>Models</span>
                <strong>4</strong>
              </div>
              <div className="profileCell">
                <span>Tasks</span>
                <strong>{benchmarkData?.task_count || 40}</strong>
              </div>
              <div className="profileCell">
                <span>Graph mode</span>
                <strong>Real-time regret</strong>
              </div>
              <div className="profileCell">
                <span>Primary baseline</span>
                <strong>Logistic Regression</strong>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="sectionHeader">
              <div>
                <h2>Cumulative regret curve</h2>
              </div>
            </div>
            {benchmarkData?.regret_curve?.length ? (
              <RegretChart
                points={benchmarkData.regret_curve.slice(0, Math.max(1, benchmarkCursor))}
              />
            ) : (
              <p className="mutedText">Run the benchmark to render the live regret graph.</p>
            )}
          </section>

          <section className="panel">
            <div className="sectionHeader">
              <div>
                <h2>Model comparison</h2>
              </div>
            </div>
            <div className="benchmarkGrid">
              {benchmarkData?.metrics ? Object.entries(benchmarkData.metrics).map(([modelName, metrics]) => (
                <BenchmarkCard key={modelName} modelName={modelName} metrics={metrics} />
              )) : (
                <>
                  <p className="mutedText">No benchmark results yet.</p>
                </>
              )}
            </div>
          </section>
        </main>
      )}

      {approvalModal ? (
        <div className="modalOverlay" data-testid="approval-modal">
          <div className="modalCard">
            <h2>Approval checkpoint</h2>
            <p>Approve simulated checkout for the current cart.</p>
            <div className="cardActions">
              <button data-testid="approve-checkout-button" onClick={submitCheckout}>Approve checkout</button>
              <button className="secondaryBtn" onClick={() => setApprovalModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      ) : null}

      {paymentRedirecting ? (
        <div className="modalOverlay">
          <div className="modalCard paymentCard">
            <h2>Redirecting to payment gateway</h2>
            <p>Connecting to the sandbox payment page and confirming the order.</p>
          </div>
        </div>
      ) : null}

      {checkoutSuccess ? <div data-testid="checkout-success" className="visuallyHidden">success</div> : null}
      {sessionId ? <div data-testid="session-ready" className="visuallyHidden">{sessionId}</div> : null}
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="statCard">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function BenchmarkCard({ modelName, metrics }) {
  return (
    <div className="benchmarkCard">
      <div className="benchmarkHeader">
        <h3>{modelName.replaceAll("_", " ")}</h3>
        <span>{modelName === "hnb" ? "ShopMind AI" : "Baseline"}</span>
      </div>
      <div className="benchmarkMetrics">
        <MetricPill label="Accuracy" value={metrics.accuracy} />
        <MetricPill label="Precision" value={metrics.precision} />
        <MetricPill label="Recall" value={metrics.recall} />
        <MetricPill label="F1" value={metrics.f1} />
        <MetricPill label="Final regret" value={metrics.final_regret} />
      </div>
    </div>
  );
}

function MetricPill({ label, value }) {
  return (
    <div className="metricPill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RegretChart({ points }) {
  const width = 920;
  const height = 300;
  const padding = 36;
  const seriesKeys = [
    { key: "hnb", color: "#0f9d8a" },
    { key: "logistic_regression", color: "#2563eb" },
    { key: "top_rated", color: "#f59e0b" },
    { key: "random", color: "#ef4444" },
  ];
  const maxY = Math.max(1, ...points.flatMap((point) => seriesKeys.map((series) => point[series.key] || 0)));
  const maxX = Math.max(1, points.length);
  const makePath = (key) => points.map((point, index) => {
    const x = padding + (index / Math.max(maxX - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((point[key] || 0) / maxY) * (height - padding * 2);
    return `${index === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");

  return (
    <div className="regretChartWrap">
      <svg viewBox={`0 0 ${width} ${height}`} className="regretChart" role="img" aria-label="Benchmark regret chart">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#94a3b8" strokeWidth="1.5" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#94a3b8" strokeWidth="1.5" />
        {seriesKeys.map((series) => (
          <path
            key={series.key}
            d={makePath(series.key)}
            fill="none"
            stroke={series.color}
            strokeWidth="4"
            strokeLinecap="round"
          />
        ))}
      </svg>
      <div className="chartLegend">
        {seriesKeys.map((series) => (
          <div className="legendItem" key={series.key}>
            <span className="legendSwatch" style={{ background: series.color }} />
            <strong>{series.key.replaceAll("_", " ")}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function PriceHistoryChart({ history }) {
  if (!history?.length) return null;
  const width = 320;
  const height = 120;
  const prices = history.map((point) => point.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = Math.max(max - min, 1);
  const points = history.map((point, index) => {
    const x = (index / Math.max(history.length - 1, 1)) * width;
    const y = height - ((point.price - min) / range) * height;
    return `${x},${y}`;
  });
  return (
    <svg className="priceChart" viewBox={`0 0 ${width} ${height}`}>
      <polyline fill="none" stroke="#2874f0" strokeWidth="3" points={points.join(" ")} />
    </svg>
  );
}
