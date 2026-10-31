// Research-use disclosures only. Never select a provider, alter observations,
// change a saved ID, or infer publication/AI/Discovery permission from this map.
const notes:Record<string,readonly string[]> = {
    gold:[
        'GC=F is a vendor continuous/front-contract futures history, not spot gold. Historical contract selection and roll adjustment are unverified; chained closes are not a verified futures total return.',
        'Daily bar labels do not establish a post-FOMC price. London gold benchmarks and the normal 13:30 ET COMEX settlement precede a typical 14:00 ET policy announcement; use verified timestamps for event research.',
    ],
    fed_funds:[
        'FEDFUNDS averages effective overnight rates over the calendar month. It cannot identify the date, size or surprise of an FOMC hike or cut; use policy statements and target-rate decisions for that question.',
        'The underlying daily effective-rate methodology changed from a volume-weighted mean to a median with the 1 March 2016 rate. Do not splice this monthly series into a daily policy-event calendar.',
    ],
    wti:[
        'CL=F is a continuous/front-contract futures price, not a physical spot benchmark or a measure of barrels produced. Roll mapping is unverified. Use a separately identified spot series for physical-market price research.',
    ],
    dxy:[
        'This is the ICE fixed six-currency dollar basket, not the Federal Reserve broad trade-weighted dollar index. A broad index is a complementary dataset, not an interchangeable historical continuation.',
    ],
    sp500:[
        'This price index excludes dividends. Use a separately identified, appropriately licensed total-return series for investment-performance questions.',
    ],
    payrolls:[
        'Establishment payroll employment counts jobs, not unique people. Published changes are revised and benchmarked; current revised values are not the data available on an historical announcement day.',
    ],
    hourly_earnings:[
        'Average earnings can change when the mix of jobs changes. This is not a fixed-composition wage measure; an employment-cost index is a useful separate comparison.',
    ],
    consumer_sentiment:[
        'The FRED feed is delayed by one month. The April–July 2024 transition from telephone to web interviews can affect comparisons. Early historical observations are sparse, not a continuous monthly sample.',
    ],
    mortgage_30y:[
        'PMMS changed to an application-based methodology on 17 November 2022. Weekly release labels are not daily borrower quotes; compare across this break with care.',
    ],
    high_yield_spread:[
        'The current FRED feed is limited to a rolling three-year history from April 2026. Do not interpret a short retrieved window as full historical credit-cycle coverage.',
    ],
    investment_grade_spread:[
        'The current FRED feed is limited to a rolling three-year history from April 2026. This index spread is not a default probability or a portfolio total return.',
    ],
};

export function researchUseNotes(id:string):readonly string[]{return Object.hasOwn(notes,id) ? notes[id] : [];}

