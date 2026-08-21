# Coursebook

```
# Introductory Statistics
### Course Coursebook

**Primary text:** *Introductory Statistics* (OpenStax), Chapters 1, 2, 11, 12, 13
**Companion slides:** OpenStax Statistics slide decks (Ch. 1, 2, 12, 13) and supplementary lecture slides on ANOVA
**Practice materials:** Seven graded problem series (Séries 1–7), each with a full worked solution set

---

## Course Overview

This course is a first-year introduction to statistical reasoning and methods. It is built around five chapters of the OpenStax *Introductory Statistics* textbook, moving from the basic vocabulary of data collection through descriptive statistics to three of the most commonly used inferential procedures: the chi-square test, correlation and linear regression, and one-way ANOVA.

Each unit pairs a book chapter and lecture slide deck with a problem series ("Série") that is completed in class or as homework and later reviewed against a full solution set. This structure is intended to move students from *definitions* → *worked examples* → *independent practice* → *feedback* within every unit.

### Learning Objectives

By the end of this course, students should be able to:

1. Distinguish between populations and samples, and identify appropriate sampling methods.
2. Organize and visualize data using appropriate plots (stem-and-leaf, histograms, box plots, scatterplots).
3. Compute and interpret measures of central tendency and spread (mean, median, mode, variance, standard deviation).
4. Perform and interpret chi-square tests of independence and goodness-of-fit.
5. Compute and interpret correlation coefficients and simple linear regression models.
6. Perform and interpret a one-way ANOVA, including reading an ANOVA table and applying post-hoc reasoning.
7. Communicate statistical findings clearly, including appropriate caveats about assumptions and limitations.

### Course Structure at a Glance

| Week | Topic | Book Chapter | Slides | Practice Série |
|------|-------|--------------|--------|-----------------|
| 1 | Sampling, Data, and Fundamentals of Statistics | Ch. 1 | OpenStax Ch. 1 | Série 1 – Fundamentals |
| 2 | Descriptive Statistics: Graphs and Plots | Ch. 2 | OpenStax Ch. 2 | Série 2 – Plots |
| 3 | Descriptive Statistics: Central Tendency & Spread | Ch. 2 | OpenStax Ch. 2 | Série 3 – Central Tendency |
| 4 | Chi-Square Tests | Ch. 11 | (Ch. 11 lecture material) | Série 4 – Chi-Square |
| 5 | Correlation | Ch. 12 | OpenStax Ch. 12 | Série 5 – Correlations |
| 6 | Linear Regression | Ch. 12 | OpenStax Ch. 12 | Série 6 – Linear Regression |
| 7 | One-Way ANOVA | Ch. 13 | OpenStax Ch. 13 / Pace slides | Série 7 – ANOVA |

---

## Unit 1 — Sampling and Data (Chapter 1)

Statistics is the science of collecting, organizing, analyzing, and interpreting data in order to make decisions under uncertainty. This unit introduces the vocabulary that underlies everything that follows.

**Key concepts**

- **Population vs. sample:** A *population* is the entire group we want to draw conclusions about; a *sample* is the subset we actually observe. Statistics computed on a sample (e.g., a sample mean) are used to estimate unknown population *parameters* (e.g., a population mean).
- **Variables:** A variable can be *qualitative* (categorical, e.g., eye color) or *quantitative* (numerical, e.g., height). Quantitative variables are further split into *discrete* (countable, e.g., number of siblings) and *continuous* (measurable, e.g., weight).
- **Levels of measurement:** nominal, ordinal, interval, and ratio scales, which determine which arithmetic and statistical operations are meaningful.
- **Sampling methods:** simple random sampling, stratified sampling, cluster sampling, systematic sampling, and convenience sampling. Random sampling methods are preferred because they help control for selection bias.
- **Sources of bias:** sampling bias, non-response bias, and self-selection bias can all distort conclusions even when the analysis itself is correct.
- **Descriptive vs. inferential statistics:** *Descriptive statistics* summarize the data at hand; *inferential statistics* use sample data to make claims about a broader population, typically with an associated measure of uncertainty (confidence intervals, p-values).

**Série 1 — Fundamentals** reinforces this vocabulary: identifying population vs. sample in short scenarios, classifying variables by type and level of measurement, and critiquing sampling designs for potential bias. The accompanying solution set walks through the reasoning for each classification, which is often more important than the label itself — students are expected to justify *why* a variable is discrete rather than continuous, or *why* a described sampling method introduces bias.

---

## Unit 2 — Descriptive Statistics: Graphs and Plots (Chapter 2, Part I)

Before summarizing data numerically, we first look at it visually. A good graph often reveals shape, outliers, and structure that summary numbers alone can hide.

**Key concepts**

- **Frequency tables:** organizing raw data into frequency, relative frequency, and cumulative relative frequency.
- **Stem-and-leaf plots:** retain the individual data values while showing overall shape — useful for small to moderate data sets.
- **Histograms:** group continuous data into bins/classes; the choice of bin width can change the apparent shape of a distribution.
- **Box plots (box-and-whisker plots):** built from the five-number summary (minimum, Q1, median, Q3, maximum); useful for comparing spread and identifying potential outliers via the 1.5×IQR rule.
- **Bar charts and pie charts:** appropriate for categorical/qualitative data, not to be confused with histograms.
- **Scatterplots:** used to visualize the relationship between two quantitative variables — a preview of the correlation and regression unit later in the course.
- **Shape vocabulary:** symmetric, skewed left, skewed right, unimodal, bimodal — and how skew affects the relative position of the mean and median.

**Série 2 — Plots** has students construct and interpret histograms, box plots, and stem-and-leaf displays from raw data sets, and asks them to describe distribution shape in words (center, spread, shape, outliers). The solutions set emphasizes correct bin selection and precise, non-generic descriptions of shape (e.g., preferring "right-skewed with a possible outlier near 95" over "the data looks spread out").

---

## Unit 3 — Descriptive Statistics: Central Tendency and Spread (Chapter 2, Part II)

**Key concepts**

- **Mean:** the arithmetic average. Sensitive to outliers.
- **Median:** the middle value of ordered data; robust to outliers and a better summary for skewed distributions.
- **Mode:** the most frequent value(s); the only measure of central tendency valid for purely categorical data.
- **Range:** maximum minus minimum — simple but sensitive to outliers.
- **Variance and standard deviation:** measure average squared (variance) or linear (standard deviation) distance from the mean. Sample variance uses an $n-1$ denominator (Bessel's correction) to give an unbiased estimate of the population variance.
- **Interquartile range (IQR):** $Q3 - Q1$, a robust measure of spread used with box plots.
- **Coefficient of variation:** standard deviation relative to the mean, useful for comparing variability across data sets with different units or scales.
- **Empirical rule / Chebyshev's theorem:** for roughly bell-shaped data, about 68%/95%/99.7% of values fall within 1/2/3 standard deviations of the mean; Chebyshev's theorem gives a weaker but distribution-free guarantee.

**Série 3 — Central Tendency** gives practice computing these statistics by hand and by calculator, choosing the *appropriate* measure of center and spread for a given distribution shape, and interpreting standard deviation in context. The solutions highlight a recurring theme: when data are skewed or contain outliers, the median and IQR are usually more informative than the mean and standard deviation.

---

## Unit 4 — Chi-Square Tests (Chapter 11)

The chi-square distribution underlies a family of hypothesis tests for categorical data.

**Key concepts**

- **Chi-square test statistic:** comparing observed counts $O_i$ to expected counts $E_i$ under a null hypothesis.
- **Goodness-of-fit test:** tests whether a single categorical variable follows a specified distribution (e.g., are dice rolls uniform?).
- **Test of independence:** tests whether two categorical variables are associated, using a contingency table; expected counts are computed as (row total × column total) / grand total.
- **Test of homogeneity:** tests whether several populations share the same distribution across categories — mechanically identical to the independence test but conceptually different in setup.
- **Degrees of freedom:** $(rows-1)(columns-1)$ for two-way tables, or $(k-1)$ for goodness-of-fit with $k$ categories.
- **Assumptions:** expected cell counts should generally be at least 5 for the chi-square approximation to be reliable.

**Série 4 — Chi-Square** has students set up contingency tables, compute expected counts, calculate the test statistic, determine degrees of freedom, and reach a decision using either a critical value or a p-value approach. The solution set pays particular attention to correctly stating the null and alternative hypotheses in each context (independence vs. goodness-of-fit are easy to conflate) and to interpreting a non-significant result correctly — failing to reject $H_0$ is not the same as proving it true.

---

## Unit 5 — Correlation (Chapter 12, Part I)

**Key concepts**

- **Scatterplots revisited:** the starting point for any bivariate analysis — direction, strength, and shape of the relationship should be assessed visually before computing any statistic.
- **Pearson correlation coefficient ($r$):** measures the strength and direction of the *linear* association between two quantitative variables, ranging from $-1$ to $+1$.
- **Interpreting $r$:** sign gives direction (positive/negative association); magnitude gives strength. $r$ near 0 does not necessarily mean "no relationship" — it means no *linear* relationship.
- **Coefficient of determination ($r^2$):** the proportion of variance in one variable explained by the linear relationship with the other; a preview of regression.
- **Correlation vs. causation:** a strong correlation never by itself establishes a causal relationship; lurking/confounding variables must be considered.
- **Limitations:** correlation is sensitive to outliers and is only meaningful for describing linear patterns.

**Série 5 — Correlations** asks students to compute $r$ from raw or summarized data, match scatterplots to correlation values, and critique causal claims made from correlational evidence. The solutions consistently reinforce that a strong $r$ describes association, not causation, and walk through at least one example with a plausible confounding variable.

---

## Unit 6 — Linear Regression (Chapter 12, Part II)

**Key concepts**

- **Simple linear regression model:** fit by the method of least squares, which minimizes the sum of squared residuals.
- **Slope ($b_1$):** the predicted change in $y$ for a one-unit increase in $x$.
- **Intercept ($b_0$):** the predicted value of $y$ when $x = 0$ — meaningful only if $x=0$ falls within (or near) the observed range of the data.
- **Residuals:** residual plots are used to check the linearity and constant-variance assumptions.
- **$r^2$ in regression:** the proportion of variability in $y$ explained by the regression line.
- **Prediction vs. extrapolation:** predictions within the range of observed $x$ values are generally reliable; predictions well outside that range (extrapolation) are not.
- **Assumptions:** linearity, independence of errors, roughly constant variance (homoscedasticity), and approximately normal residuals.

**Série 6 — Linear Regression** has students fit a regression line to a bivariate data set, interpret the slope and intercept in context, compute and interpret $r^2$, and use the fitted equation to make predictions — while flagging cases where extrapolation would be inappropriate. The solutions emphasize units and context in every interpretation (e.g., "for each additional hour studied, predicted exam score increases by 2.3 points," not just "the slope is 2.3").

---

## Unit 7 — One-Way ANOVA (Chapter 13)

The course closes with Analysis of Variance, which extends the two-sample comparison-of-means idea to three or more groups.

**Key concepts**

- **Purpose:** ANOVA tests whether the means of three or more independent groups are all equal, avoiding the inflated Type I error rate that would result from running many pairwise t-tests.
- **Between-group vs. within-group variance:** ANOVA compares variability *between* group means to variability *within* groups.
- **F-statistic:** A large $F$ suggests that between-group differences are large relative to natural variability within groups.
- **ANOVA table:** organizes sums of squares (SSB, SSW, SST), degrees of freedom, mean squares, the F-statistic, and the p-value.
- **Assumptions:** independent samples, approximately normal populations, and approximately equal variances across groups (homogeneity of variance).
- **Interpreting a significant result:** a significant ANOVA tells us *at least one* group mean differs from the others, but not *which* ones — this motivates post-hoc comparisons (mentioned conceptually, e.g., Tukey's HSD), which distinguish specific pairs of group means that differ.

**Série 7 — ANOVA** has students construct a full one-way ANOVA table by hand from raw group data, interpret the F-statistic and p-value, and state conclusions in the context of the original research question. The solution set walks through each cell of the ANOVA table step by step and reiterates that a significant F-test is the beginning, not the end, of the analysis — the natural next question ("which groups differ?") sets up further coursework beyond this introductory unit.

---

*This coursebook is a study companion synthesizing the assigned textbook chapters, lecture slides, and practice series for this course. It is not a substitute for the primary readings (OpenStax Introductory Statistics, Chapters 1, 2, 11, 12, 13) or for attending lecture.*
```
