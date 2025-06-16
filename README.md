<h1 align="center">Symulator Robota PUMA o 6 stopniach swobodyF</h1>

<p align="center">
Symulator ramienia robota <b>PUMA</b> z sześcioma stopniami swobody, zbudowany w Pythonie z użyciem <b>PyOpenGL</b> i <b>ikpy</b>.
<br>Umożliwia animowaną kontrolę robota, inverse kinematics, chwytanie kuli i unikanie kolizji z podłogą.
</p>

---

## ✨ Funkcje

-  <b>Płynna animacja</b> ruchów robota między pozycjami
-  <b>Inverse Kinematics</b> – odwrotna kinematyka przy użyciu <code>ikpy</code>
-  <b>Symulowany chwytak</b> z hakami lub palcami – umożliwia chwytanie obiektów
-  <b>Kamera sferyczna</b> – sterowanie widokiem (obrót, zoom)
-  <b>Interaktywna kostka</b> – można ją chwytać, podnosić i upuszczać
-  <b>Detekcja kolizji</b> – zapobiega wchodzeniu robota pod podłogę
- 🌫 <b>Oświetlenie i mgła</b> – dla lepszego wyglądu 3D

---

## Sterowanie klawiaturą

| Klawisz | Działanie |
|--------|-----------|
| <code>z/x</code>  | obrót stawu 1 |
| <code>m/n</code>  | obrót stawu 2 |
| <code>u/i</code>  | obrót stawu 3 |
| <code>j/h</code>  | obrót stawu 4 |
| <code>l/;</code>  | obrót stawu 5 |
| <code>t/y</code>  | obrót stawu 6 |
| <code>o</code>    | otwieranie/zamykanie chwytaka |
| <code>g</code>    | złap/upuść kostkę |
| <code>k</code>, <code>q</code> | automatyczne podejście i chwytanie kostki |
| <code>e</code>    | ręczne wprowadzenie współrzędnych celu |
| <code>f</code>    | wyświetlenie pozycji TCP |
| <code>a/d/w/s/+/-</code> | obrót/zoom kamery |

---

## ⚙️ Wymagania

- Python 3.x  
- Biblioteki:
  ```bash
  pip install PyOpenGL PyOpenGL_accelerate ikpy numpy
