import streamlit as st
import pandas as pd
import plotly.express as px

# Custom CSS to style slider labels
st.markdown("""
    <style>
    .slider-label {
        font-size: 18px;
        font-weight: bold;
    }
    .header {
        font-size: 18px; /* Adjust the font size as needed */
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Create the Streamlit app
st.title("Safe Withdrawal Rate Calculator")
st.text("This calculator allows you to forecast the optimal withdrawal rate for various")
st.text("portfolio asset allocations. Choose between two retirement withdrawal")
st.text("strategies: the Dollar Plus Inflation Spending Rule and the Dynamic")
st.text("Spending Rule.")


# Fee slider selection
st.markdown('<div class="slider-label">Select Portfolio Fee (%)</div>', unsafe_allow_html=True)
fee_rate = st.slider("Fee Rate", min_value=0.0, max_value=2.0, value=0.0, step=0.1, label_visibility="collapsed") / 100

# Load the  data
file_path = "All Indices Annual Returns.csv"
data = pd.read_csv(file_path)

# Ensure the index is the year only
data.set_index('Dates', inplace=True)

# Define the available assets
available_assets = {
    'US Stocks': 'us_stocks',
    'US Bonds': 'us_bonds',
    'International Stocks': 'intl_stocks',
    'International Bonds': 'intl_bonds'
}

# Default weights for assets
default_weights = {
    'US Stocks': 100,
    'US Bonds': 0,
    'International Stocks': 0,
    'International Bonds': 0
}

# Title for the asset allocation section
st.header("Asset Allocation")

# Create inputs for each asset weight
weights = {}
total_weight = 0
for asset in available_assets.keys():
    weight = st.number_input(f'Allocation for {asset}', min_value=0, max_value=100, step=1, value=default_weights[asset], key=f'weight_{asset}')
    weights[asset] = weight / 100
    total_weight += weight

# Check if the total weight sums to 100%
if total_weight != 100:
    st.error("The total weight must sum to 100%. Please adjust the weights.")
else:
    # Calculate annual returns for each selected asset
    selected_indices = [available_assets[asset] for asset in available_assets.keys()]
    annual_returns = data[selected_indices].copy()

    # Compute the weighted portfolio returns
    portfolio_weights = [weights[asset] for asset in available_assets.keys()]
    portfolio_returns = (annual_returns * portfolio_weights).sum(axis=1)

    # Add the portfolio returns to the DataFrame
    annual_returns.loc[:, 'Portfolio Returns'] = portfolio_returns

    st.write("Portfolio returns calculated successfully.")

st.header("Dollar Plus Strategy")
# Implementing the Dollar Plus strategy
# Parameters for the Dollar Plus strategy
initial_portfolio = 1000000  # Initial portfolio amount
# withdrawal_rates = [0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07, 0.075, 0.08, 0.085, 0.09, 0.095, 0.1,
#                    0.105, 0.11, 0.115, 0.12]  # Withdrawal rates from 3% to 12%
withdrawal_rates = [0.03 + i * 0.0025 for i in range(37)]  # Withdrawal rates from 3% to 12%

payout_periods = [30, 40, 50]  # Payout periods

# Convert annual returns to the selected portfolio returns
selected_returns = annual_returns['Portfolio Returns']
annual_inflation_rates = data['inflation']

# Function to calculate success scores
def calculate_success_scores(returns, inflation, withdrawal_rate, fee_rate, payout_periods):
    success_scores = {}
    for payout_period in payout_periods:
        success_list = []
        for start_year in range(len(returns) - payout_period + 1):
            end_year = start_year + payout_period
            portfolio_value = initial_portfolio
            adjusted_withdrawal_amount = initial_portfolio * withdrawal_rate
            success = 1  # Assume success unless proven otherwise

            for i in range(start_year, end_year):
                if i > start_year:  # Skip the first year for inflation adjustment
                    adjusted_withdrawal_amount *= (1 + inflation.iloc[i - 1])

                end_of_year_value = (portfolio_value * (1 + returns.iloc[i]) * (
                            1 - fee_rate)) - adjusted_withdrawal_amount
                portfolio_value = end_of_year_value

                if portfolio_value <= 0:
                    success = 0
                    break

            success_list.append({
                'Beginning of payout period': data.index[start_year],
                'End of payout period': data.index[end_year - 1],
                'Success': success
            })

        success_df = pd.DataFrame(success_list)
        success_scores[payout_period] = success_df['Success'].mean()

    return success_scores


# Calculate success scores for different withdrawal rates and payout periods
success_scores_dict = {
    rate: calculate_success_scores(selected_returns, annual_inflation_rates, rate, fee_rate, payout_periods) for rate in
    withdrawal_rates}

# Create a DataFrame for the success scores
success_scores_df = pd.DataFrame(success_scores_dict).T
success_scores_df.columns = [f'Payout Period {period} years' for period in payout_periods]
success_scores_df.reset_index(inplace=True)
success_scores_df.rename(columns={'index': 'Withdrawal Rate'}, inplace=True)

# Function to filter the DataFrame to drop all entries after the first zero in 'Payout Period 30 years'
def filter_success_scores(df, column):
    zero_indices = df[df[column] == 0].index
    if len(zero_indices) > 0:
        first_zero_index = zero_indices[0]
        filtered_df = df.iloc[:first_zero_index + 1]
    else:
        filtered_df = df
    return filtered_df

# Filter the DataFrame
filtered_success_scores_df = filter_success_scores(success_scores_df, 'Payout Period 30 years')

# Plot the filtered success scores using Plotly
# Revised Plotly code to meet the specified requirements
fig = px.line(
    filtered_success_scores_df,
    x='Withdrawal Rate',
    y=filtered_success_scores_df.columns[1:],
    title='Success Rates for Different Payout Periods (Dollar Plus Strategy)',
    labels={'value': 'Success Rate (%)', 'Withdrawal Rate': 'Withdrawal Rate (%)'}
)

# Update line colors for specific payout periods
color_map = {
    'Payout Period 30 years': 'blue',
    'Payout Period 40 years': 'goldenrod',
    'Payout Period 50 years': 'red'
}

for line in fig.data:
    line_name = line.name
    if line_name in color_map:
        line.line.color = color_map[line_name]

# Update axis format to percentage and add gridlines
fig.update_layout(
    xaxis=dict(
        tickformat=".0%",  # Display X axis as percentage
        showgrid=True,     # Add gridlines to X axis
        title='Withdrawal Rate (%)',
        dtick=0.01,        # Set x-axis ticks at 1% increments
    ),
    yaxis=dict(
        tickformat=".0%",  # Display Y axis as percentage
        showgrid=True,     # Add gridlines to Y axis
        title='Success Rate (%)',
        dtick=0.1,         # Set y-axis ticks at 10% increments
        range=[0, 1]       # Set range from 0% to 100%
    ),
    title=dict(
        text='Success Rates for Different Payout Periods (Dollar Plus Strategy)',
        x=0,  # Set title position to the left
        xanchor='left'  # Align title to the left
    ),
    legend_title_text=''  # Remove the legend title
)

# Ensure hover labels display success rates for all withdrawal rates including increments of 0.5%
fig.update_traces(
    hovertemplate='<b>%{fullData.name}</b><br>Withdrawal rate: %{x:.2%}<br>Success rate: %{y:.2%}<extra></extra>'
)

# Plot the figure
st.plotly_chart(fig)

# Convert all entries to percentages and add the '%' symbol
filtered_success_scores_df_percentages = filtered_success_scores_df.copy()
for column in filtered_success_scores_df_percentages.columns:
    filtered_success_scores_df_percentages[column] = filtered_success_scores_df_percentages[column].apply(lambda x: f"{x * 100:.2f}%")

# Reset the index and drop the index column
filtered_success_scores_df_percentages.reset_index(drop=True, inplace=True)

# Print the data frame with the success score values for each withdrawal rate
with st.expander("Success Rate Data for the Dollar Plus Strategy"):
    st.write(filtered_success_scores_df_percentages)

st.header("Dynamic Spending Rule")
# Define the ceiling growth and floor shrink rates
ceiling_growth = 0.05  # Ceiling growth rate
floor_shrink = 0.015  # Floor shrink rate

# Function to calculate success scores for the Dynamic Spending Rule strategy
def calculate_dynamic_success_scores(returns, inflation, withdrawal_rate, fee_rate, ceiling_growth, floor_shrink,
                                     payout_periods):
    success_scores = {}
    for payout_period in payout_periods:
        success_list = []
        for start_year in range(len(returns) - payout_period + 1):
            end_year = start_year + payout_period
            portfolio_value = initial_portfolio
            adjusted_withdrawal_amount = initial_portfolio * withdrawal_rate
            success = 1  # Assume success unless proven otherwise

            # Year 1 calculations
            nominal_ending = initial_portfolio * (1 + returns.iloc[start_year]) * (1 - fee_rate)
            real_ending = nominal_ending
            withdrawal = withdrawal_rate * real_ending

            # Save the initial withdrawal amount for use in ceiling and floor calculations for year 2 onwards
            previous_withdrawal = withdrawal

            # Store results for Year 1
            portfolio_value = real_ending - withdrawal

            # Years 2 onwards
            for i in range(start_year + 1, end_year):
                nominal_ending = portfolio_value * (1 + returns.iloc[i]) * (1 - fee_rate)
                real_ending = nominal_ending / (1 + inflation.iloc[i])
                withdrawal = withdrawal_rate * real_ending

                # Calculate ceiling and floor based on previous year's withdrawal amount
                ceiling = previous_withdrawal * (1 + ceiling_growth)
                floor = previous_withdrawal * (1 - floor_shrink)
                withdrawal = max(min(withdrawal, ceiling), floor)

                # Update the previous withdrawal for the next year's calculations
                previous_withdrawal = withdrawal

                portfolio_value = real_ending - withdrawal

                if portfolio_value <= 0:
                    success = 0
                    break

            success_list.append({
                'Beginning of payout period': returns.index[start_year],
                'End of payout period': returns.index[end_year - 1],
                'Success': success
            })

        success_df = pd.DataFrame(success_list)
        success_scores[payout_period] = success_df['Success'].mean()

    return success_scores

# Calculate success scores for different withdrawal rates and payout periods for Dynamic Spending Rule
dynamic_success_scores_dict = {
    rate: calculate_dynamic_success_scores(selected_returns, annual_inflation_rates, rate, fee_rate, ceiling_growth,
                                           floor_shrink, payout_periods)
    for rate in withdrawal_rates
}

# Create a DataFrame for the success scores
dynamic_success_scores_df = pd.DataFrame(dynamic_success_scores_dict).T
dynamic_success_scores_df.columns = [f'Payout Period {period} years' for period in payout_periods]
dynamic_success_scores_df.reset_index(inplace=True)
dynamic_success_scores_df.rename(columns={'index': 'Withdrawal Rate'}, inplace=True)

# Function to filter the DataFrame to drop all entries after the first zero in 'Payout Period 30 years'
def filter_success_scores(df, column):
    zero_indices = df[df[column] == 0].index
    if len(zero_indices) > 0:
        first_zero_index = zero_indices[0]
        filtered_df = df.iloc[:first_zero_index + 1]
    else:
        filtered_df = df
    return filtered_df

# Filter the DataFrame
filtered_dynamic_success_scores_df = filter_success_scores(dynamic_success_scores_df, 'Payout Period 30 years')

# Plot the filtered success scores using Plotly
# Revised Plotly code to meet the specified requirements
fig = px.line(
    filtered_dynamic_success_scores_df,
    x='Withdrawal Rate',
    y=filtered_dynamic_success_scores_df.columns[1:],
    title='Success Rates for Different Payout Periods (Dynamic Spending Rule)',
    labels={'value': 'Success Rate (%)', 'Withdrawal Rate': 'Withdrawal Rate (%)'}
)

# Update line colors for specific payout periods
color_map = {
    'Payout Period 30 years': 'blue',
    'Payout Period 40 years': 'goldenrod',
    'Payout Period 50 years': 'red'
}

for line in fig.data:
    line_name = line.name
    if line_name in color_map:
        line.line.color = color_map[line_name]

# Update axis format to percentage and add gridlines
fig.update_layout(
    xaxis=dict(
        tickformat=".0%",  # Display X axis as percentage
        showgrid=True,     # Add gridlines to X axis
        title='Withdrawal Rate (%)',
        dtick=0.01,        # Set x-axis ticks at 1% increments
    ),
    yaxis=dict(
        tickformat=".0%",  # Display Y axis as percentage
        showgrid=True,     # Add gridlines to Y axis
        title='Success Rate (%)',
        dtick=0.1,         # Set y-axis ticks at 10% increments
        range=[0, 1]       # Set range from 0% to 100%
    ),
    title=dict(
        text='Success Rates for Different Payout Periods (Dynamic Spending Rule)',
        x=0,  # Set title position to the left
        xanchor='left'  # Align title to the left
    ),
    legend_title_text=''  # Remove the legend title
)

# Ensure hover labels display success rates for all withdrawal rates including increments of 0.25%
fig.update_traces(
    hovertemplate='<b>%{fullData.name}</b><br>Withdrawal rate: %{x:.2%}<br>Success rate: %{y:.2%}<extra></extra>'
)

# Plot the figure
st.plotly_chart(fig)

# Convert all entries to percentages and add the '%' symbol
filtered_dynamic_success_scores_df_percentages = filtered_dynamic_success_scores_df.copy()
for column in filtered_dynamic_success_scores_df_percentages.columns:
    filtered_dynamic_success_scores_df_percentages[column] = filtered_dynamic_success_scores_df_percentages[column].apply(lambda x: f"{x * 100:.2f}%")

# Reset the index and drop the index column
filtered_dynamic_success_scores_df_percentages.reset_index(drop=True, inplace=True)

# Display and save the updated DataFrame with percentages
with st.expander("Success Rate Data for the Dynamic Spending Rule Strategy"):
    st.write(filtered_dynamic_success_scores_df_percentages)


# Add links to your YouTube channel and Instagram at the bottom of the app
youtube_url = "https://www.youtube.com/@itsrosehan"
website_url = "https://rosehan.com/"

st.markdown(
    f"""
    <div style="position: fixed; bottom: 0; width: 100%; text-align: center; background-color: white; padding: 10px; border-top: 1px solid #eaeaea;">
        <a href="{youtube_url}" target="_blank" style="text-decoration: none; color: #0366d6; margin-right: 20px;">
            Check out my YouTube channel
        </a>
        <a href="{website_url}" target="_blank" style="text-decoration: none; color: #0366d6;">
            Check out my Web Site
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
