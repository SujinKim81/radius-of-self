const listEl = document.querySelector("[data-essay-list]");

function normalizeUrl(item) {
  if (item.url) {
    return item.url;
  }
  return `article/${item.slug}/`;
}

function renderPeople(people) {
  const sorted = [...people].sort((a, b) => String(b.date).localeCompare(String(a.date)));
  listEl.replaceChildren();

  if (sorted.length === 0) {
    listEl.innerHTML = '<p class="empty">아직 공개된 글이 없습니다.</p>';
    return;
  }

  sorted.forEach((item) => {
    const article = document.createElement("a");
    article.className = "article";
    article.href = normalizeUrl(item);

    const date = document.createElement("p");
    date.className = "date";
    date.textContent = item.date;

    const title = document.createElement("h2");
    title.className = "title";
    title.textContent = item.name;

    const summary = document.createElement("p");
    summary.className = "summary";
    summary.textContent = item.summary;

    article.append(date, title, summary);
    listEl.append(article);
  });
}

async function loadPeople() {
  try {
    const response = await fetch("./data/people.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`people.json ${response.status}`);
    }
    const people = await response.json();
    renderPeople(Array.isArray(people) ? people : people.people || []);
  } catch (error) {
    console.error(error);
    listEl.innerHTML = '<p class="empty">글 목록을 불러오지 못했습니다.</p>';
  }
}

loadPeople();
