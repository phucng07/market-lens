# Independent base-R validation. Run from the repository root.
d <- read.csv('data/processed/city_year_data.csv', na.strings=c('', 'NA'))
proxy <- 1200 * d$median_gross_rent_nominal / d$median_household_income_nominal
metric_error <- max(abs(proxy - d$annual_rent_to_income_pct), na.rm=TRUE)
stopifnot(metric_error < 1e-9)
base_cpi <- d$cpi[d$year == max(d$year)][1]
real_income <- d$median_household_income_nominal * base_cpi / d$cpi
inflation_error <- max(abs(real_income - d$median_household_income_real), na.rm=TRUE)
stopifnot(inflation_error < 1e-7)
s <- d[complete.cases(d[,c('annual_rent_to_income_pct','vacancy_rate')]),]
s$minneapolis <- as.numeric(s$city == 'Minneapolis')
s$time_trend <- s$year - 2010
model <- lm(annual_rent_to_income_pct ~ vacancy_rate + minneapolis + time_trend, data=s)
X <- model.matrix(model)
bread <- solve(t(X) %*% X)
omega <- residuals(model)^2 / (1 - hatvalues(model))^2
hc3 <- bread %*% (t(X) %*% (X * omega)) %*% bread
se <- sqrt(diag(hc3))
py <- read.csv('data/results/regression_coefficients.csv')
expected_names <- c('const','vacancy_rate','minneapolis','time_trend')
stopifnot(identical(py$term, expected_names))
coefficient_error <- max(abs(unname(coef(model)) - py$coefficient))
se_error <- max(abs(unname(se) - py$robust_se))
stopifnot(coefficient_error < 1e-8, se_error < 1e-8)
dir.create('data/results', recursive=TRUE, showWarnings=FALSE)
write.csv(data.frame(term=expected_names, coefficient=unname(coef(model)), robust_se=unname(se)),
          'data/results/r_regression_coefficients.csv', row.names=FALSE)
png('figures/r_validation_proxy.png', width=1500, height=850, res=150)
par(mar=c(5,5,4,2))
colors <- c(Madison='#176b87', Minneapolis='#b65b2a')
plot(range(d$year), range(proxy,na.rm=TRUE), type='n', xlab='Year',
     ylab='Annualized rent-to-income proxy (%)', main='Independent R calculation of the affordability proxy')
for (city in names(colors)) {
  i <- d$city == city
  lines(d$year[i], proxy[i], type='o', col=colors[city], pch=16)
}
legend('topleft', legend=names(colors), col=colors, lty=1, pch=16, bty='n')
mtext('Source: U.S. Census Bureau, ACS 1-year. 2020 missing; no interpolation.', side=1, line=3.5, cex=.8)
dev.off()
cat(sprintf('PASS: proxy error %.3g; inflation error %.3g; OLS coefficient error %.3g; HC3 SE error %.3g\n',
            metric_error, inflation_error, coefficient_error, se_error))
