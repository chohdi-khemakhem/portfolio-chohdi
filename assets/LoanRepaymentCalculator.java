package schedule;

import java.text.DecimalFormat;
import java.text.SimpleDateFormat;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.Date;

public class LoanRepaymentCalculator {
    public static final int TYPE_IN_FINE = 1;
    public static final int TYPE_CONSTANT_AMORTIZATION = 2;
    public static final int TYPE_SPECIFIC_REPAYMENT = 3;

    public static void main(String[] args) {
        // Paramètres du prêt
        double loanAmount = 119804;
        double annualInterestRate = 0.065;
        int period = 130;
        int paymentFrequency = 1;
        int calculationBase = 2;
        int repaymentType = 3; 
        
        // Paramètres supplémentaires pour le type spécifique
        int interestFrequency = 1;
        int deferredPeriod = 0;
        boolean flat = false;
        double feeAmount = 200;

        // Dates
        LocalDate disbursementDate = LocalDate.of(2025, 4, 29);
        LocalDate firstInstallmentDate = LocalDate.of(2025, 5, 29);

        // Calcul selon le type de remboursement
        switch (repaymentType) {
            case TYPE_IN_FINE:
                calculateInFine(loanAmount, annualInterestRate, period, paymentFrequency, 
                               calculationBase, disbursementDate, firstInstallmentDate);
                break;
            case TYPE_CONSTANT_AMORTIZATION:
                calculateConstantAmortization(loanAmount, annualInterestRate, period, paymentFrequency, 
                                            calculationBase, disbursementDate, firstInstallmentDate);
                break;
            case TYPE_SPECIFIC_REPAYMENT:
                calculateSpecificRepayment(loanAmount, annualInterestRate, period, interestFrequency, 
                                         paymentFrequency, deferredPeriod, flat, feeAmount, 
                                         calculationBase, disbursementDate, firstInstallmentDate);
                break;
            default:
                System.out.println("Type de remboursement non reconnu");
        }
    }

    // Méthode pour le calcul in fine
    public static void calculateInFine(double loanAmount, double annualInterestRate, int period, 
                                     int paymentFrequency, int calculationBase, 
                                     LocalDate disbursementDate, LocalDate firstInstallmentDate) {
        double periodicRate = calculatePeriodicRate(annualInterestRate, paymentFrequency, calculationBase);
        
        DecimalFormat df = new DecimalFormat("#.##");
        SimpleDateFormat sdf = new SimpleDateFormat("dd/MM/yyyy");

        double interest = loanAmount * periodicRate;
        double remainingBalance = loanAmount;

        System.out.println("Période\t\tDate\t\tVersement\tIntérêt\t\tPrincipal\tSolde restant");

        LocalDate date = firstInstallmentDate;

        for (int i = 1; i <= period; i++) {
            double principal = 0;
            double payment;

            if (i == period) {
                principal = loanAmount;
            }

            payment = interest + principal;
            remainingBalance -= principal;

            printPaymentLine(i, date, payment, interest, principal, remainingBalance, df, sdf);

            date = date.plusMonths(paymentFrequency);
        }
    }

    // Méthode pour le calcul avec amortissement constant
    public static void calculateConstantAmortization(double loanAmount, double annualInterestRate, int period, 
                                                   int paymentFrequency, int calculationBase, 
                                                   LocalDate disbursementDate, LocalDate firstInstallmentDate) {
        double periodicRate;
        double dailyRate = 0;
        if (calculationBase == 1) {
            periodicRate = annualInterestRate * paymentFrequency / 12;
        } else {
            dailyRate = annualInterestRate / 360;
            periodicRate = annualInterestRate * paymentFrequency * 30.478 / 360;
        }

        DecimalFormat df = new DecimalFormat("#.##");
        SimpleDateFormat sdf = new SimpleDateFormat("dd/MM/yyyy");

        double amortization = loanAmount / period;
        double remainingBalance = loanAmount;

        System.out.println("Période\t\tDate\t\tVersement\tIntérêt\t\tPrincipal\tSolde restant");

        LocalDate date = firstInstallmentDate;
        for (int i = 1; i <= period; i++) {
            double interest;
            long days;
            if (i == 1) {
                days = ChronoUnit.DAYS.between(disbursementDate, date);
            } else {
                days = ChronoUnit.DAYS.between(date.minusMonths(paymentFrequency), date);
            }

            if (calculationBase == 1) {
                interest = remainingBalance * periodicRate;
            } else {
                interest = remainingBalance * dailyRate * days;
            }

            double payment = amortization + interest;
            remainingBalance -= amortization;

            printPaymentLine(i, date, payment, interest, amortization, remainingBalance, df, sdf);

            date = date.plusMonths(paymentFrequency);
        }
    }

    // Méthode pour le calcul avec remboursement spécifique
    public static void calculateSpecificRepayment(double loanAmount, double annualInterestRate, int period, 
                                                int interestFrequency, int paymentFrequency, 
                                                int deferredPeriod, boolean flat, double feeAmount, 
                                                int calculationBase, LocalDate disbursementDate, 
                                                LocalDate firstInstallmentDate) {
        double rate;
        if (flat) {
            double monthlyRate = (annualInterestRate * interestFrequency) / 12;
            double installmentAmount = loanAmount * (monthlyRate + 1.0 / (period / paymentFrequency));
            installmentAmount = installmentAmount * (period / paymentFrequency) / ((period / paymentFrequency) - deferredPeriod);
            double totalInterest = (installmentAmount * ((period / paymentFrequency) - deferredPeriod)) - loanAmount;
            
            double estimatedRate = 0.01;
            double epsilon = 0.000001;
            rate = calculateInterestRate(installmentAmount, period, loanAmount, estimatedRate, epsilon, paymentFrequency, deferredPeriod);
        } else {
            rate = annualInterestRate;
        }
        
        calculateSchedule(rate, loanAmount, period, interestFrequency, paymentFrequency, 
                         deferredPeriod, feeAmount, disbursementDate, firstInstallmentDate, calculationBase);
    }

    // Méthodes utilitaires communes
    private static double calculatePeriodicRate(double annualRate, int frequency, int calculationBase) {
        if (calculationBase == 1) {
            return annualRate * frequency / 12;
        } else {
            return annualRate * frequency * 30.478 / 360;
        }
    }

    private static void printPaymentLine(int period, LocalDate date, double payment, double interest, 
                                       double principal, double remainingBalance, 
                                       DecimalFormat df, SimpleDateFormat sdf) {
        Date displayDate = Date.from(date.atStartOfDay(ZoneId.systemDefault()).toInstant());
        System.out.println(period + "\t\t" + sdf.format(displayDate) + "\t" +
                df.format(payment) + "\t\t" +
                df.format(interest) + "\t\t" +
                df.format(principal) + "\t\t" +
                df.format(remainingBalance));
    }

    // Méthodes pour le calcul spécifique (conservées de l'original)
    public static double calculateInterestRate(double vpm, int period, double amount, 
                                            double estimatedRate, double epsilon, 
                                            int frequency, int deferredPeriod) {
        // Implémentation originale conservée
        double rate = estimatedRate;
        double error = Double.MAX_VALUE;
        period = (period / frequency) - deferredPeriod;
        int iterations = 0;
        while (error > epsilon) {
            double vpmEstimated = calculateVPM(rate, period, amount);
            double derivative = (amount * (period * frequency + deferredPeriod * frequency)) * Math.pow(1 + rate, -period - 1);
            
            double newEstimation = rate - (vpmEstimated - vpm) / derivative;
            
            error = Math.abs(newEstimation - rate);
            rate = newEstimation;
            iterations++;
        }
        
        return rate * 12 / frequency;
    }

    public static double calculateVPM(double rate, int period, double amount) {
        double vpm = (rate * amount) / (1 - Math.pow(1 + rate, -period));
        return vpm;
    }

    public static void calculateSchedule(double rate, double amount, int period, 
                                       int interestFrequency, int paymentFrequency, 
                                       int deferredPeriod, double feeAmount, 
                                       LocalDate disbursementDate, LocalDate firstInstallmentDate, 
                                       int calculationBase) {
        // Implémentation originale conservée
        int adjustedPeriod = period / interestFrequency;
        double dailyRate = 0;
        if (calculationBase == 1) {
            rate = rate * interestFrequency / 12;
        } else { 
            dailyRate = rate / 360;
            rate = rate * interestFrequency * 30.478 / 360;
        }

        double vpm = (rate * amount) / (1 - Math.pow(1 + rate, -((period / paymentFrequency) - deferredPeriod)));
        double[] tab = new double[adjustedPeriod];

        DecimalFormat decimalFormat = new DecimalFormat("#.##");
        SimpleDateFormat dateFormat = new SimpleDateFormat("dd/MM/yyyy");
        System.out.println("Montant du versement périodique : " + decimalFormat.format(vpm));

        double remainingBalance = amount;
        System.out.println("Tableau d'échéancier :");
        System.out.println("Période\t\tDate\t\tVersement\tIntérêt\t\tPrincipal\tSolde restant");
        
        long days = 0;
        LocalDate calendarDate = firstInstallmentDate;
        double interestDiff = 0;
        double totalPayment = 0;
        double totalInterest = 0;
        double totalPrincipal = 0;
        
        for (int i = 1; i <= adjustedPeriod; i++) {
            double principal = 0;
            double payment = 0;
            double interest = 0;
            
            if (i <= deferredPeriod) {
                interest = 0;
            } else {
                if (i == 1) {  
                    days = ChronoUnit.DAYS.between(disbursementDate, calendarDate);
                } else {
                    days = ChronoUnit.DAYS.between(calendarDate.minusMonths((int) interestFrequency), calendarDate);
                }

                if (calculationBase == 1) { 
                    interest = remainingBalance * rate;
                } else {
                    interest = remainingBalance * dailyRate * days;
                }

                if (i % (paymentFrequency / interestFrequency) == 0) {
                    payment = vpm;
                    if (payment < interestDiff + interest) {
                        interestDiff = interestDiff + interest - payment;
                        interest = payment;
                    } else {
                        if (interestDiff != 0) {
                            interest = interestDiff + interest;
                            interestDiff = 0;
                        }
                    }

                    if (i == adjustedPeriod) {
                        payment = remainingBalance + interest;
                    }
                    principal = payment - interest;
                } else {
                    payment = interest;
                }
            }
            
            remainingBalance -= principal;
            totalPayment += payment;
            totalInterest += interest;
            totalPrincipal += principal;

            Date date = Date.from(calendarDate.atStartOfDay(ZoneId.systemDefault()).toInstant());
            System.out.println(i + "\t\t" + dateFormat.format(date) + "\t" +
                    decimalFormat.format(payment) + "\t\t" +
                    decimalFormat.format(interest) + "\t\t" +
                    decimalFormat.format(principal) + "\t\t" +
                    decimalFormat.format(remainingBalance));

            tab[i-1] = payment;
            calendarDate = calendarDate.plusMonths((int) interestFrequency);
        }

        System.out.println("\t\t\t\t" + decimalFormat.format(totalPayment) + "\t" + 
                         decimalFormat.format(totalInterest) + "\t\t" +
                         decimalFormat.format(totalPrincipal));

        double t = findT(amount, feeAmount, vpm, period, interestFrequency, deferredPeriod, 
                        tab, disbursementDate, firstInstallmentDate);
        double result = Math.pow(1 + t, (12 / interestFrequency)) - 1;
        System.out.println("La valeur de TEG est : " + result * 100 + "%");
    }

    public static double findT(double loanAmount, double feeAmount, double installmentAmount, 
                             int period, double interestFrequency, int deferredPeriod, 
                             double[] tab, LocalDate disbursementDate, LocalDate firstInstallmentDate) {
        // Implémentation originale conservée
        double a = 0.00;
        double b = 1.10;
        double epsilon = 0.00001;

        int adjustedPeriod1 = (int) (period / interestFrequency);
        LocalDate date0 = firstInstallmentDate.minusMonths((int) interestFrequency);
        long intermediatePeriod = ChronoUnit.DAYS.between(disbursementDate, date0);

        if (intermediatePeriod > (30 * interestFrequency) / 2) {
            int k = (int) Math.round(intermediatePeriod / (30 * interestFrequency));
            adjustedPeriod1 = (int) (period / interestFrequency) + k;
            double[] tab1 = new double[adjustedPeriod1];
            for (int j = 1; j <= k; j++) {
                tab1[j-1] = 0;
            }

            for (int i = k; i <= adjustedPeriod1 - 1; i++) {
                tab1[i] = tab[i-k];
            }
            tab = tab1;
        }

        double fa = computeFunctionValue(a, loanAmount, feeAmount, installmentAmount, period, 
                                       interestFrequency, deferredPeriod, tab, adjustedPeriod1);
        double fb = computeFunctionValue(b, loanAmount, feeAmount, installmentAmount, period, 
                                       interestFrequency, deferredPeriod, tab, adjustedPeriod1);

        if (fa * fb >= 0) {
            System.out.println("La fonction n'a pas de racine dans l'intervalle spécifié.");
            return Double.NaN;
        }

        double c;
        do {
            c = (a + b) / 2.0;
            double fc = computeFunctionValue(c, loanAmount, feeAmount, installmentAmount, period, 
                                          interestFrequency, deferredPeriod, tab, adjustedPeriod1);

            if (fa * fc < 0) {
                b = c;
                fb = fc;
            } else {
                a = c;
                fa = fc;
            }
        } while (Math.abs(b - a) > epsilon);

        return (a + b) / 2.0;
    }

    public static double computeFunctionValue(double t, double loanAmount, double feeAmount, 
                                           double installmentAmount, int period, 
                                           double interestFrequency, int deferredPeriod, 
                                           double[] tab, int adjustedPeriod1) {
        double result = loanAmount - feeAmount;

        for (int i = 1; i <= adjustedPeriod1; i++) {
            result -= tab[i-1] / Math.pow((1 + t), i);
        }

        return result;
    }
}