from preprocessing import *
from filtering import *
from utils import *
import datetime
import pickle

import argparse

parser = argparse.ArgumentParser(description="Detect Craters in PointCloud")

parser.add_argument('-infile', required=True,  help='Path to Input File (TXT/LAS)')
parser.add_argument('-outfile', required=True, help='Path to Output Pointcloud (txt)')
parser.add_argument('-out_shp', required=True, help='Path to Output Bounding Boxes (shp)')
parser.add_argument('-method', default="Filter", help='Used Method ["Filter", "DecisionTree", "RandomForest"]')
parser.add_argument('-clip', default=False, help='Clip to extent? (Boolean)')
parser.add_argument('-extent', required=False, help='Extent ("xmin, ymin, xmax, ymax"')
parser.add_argument('-keep_tmp', default=False, help='Save temporary files in folder "tmp" of this directory? (Boolean)')

args = parser.parse_args()

if args.method not in ["Filter", "DecisionTree", "RandomForest"]:
    print('Please provide a -method argument. Possible methods: ["Filter", "DecisionTree", "RandomForest"]')

else:
    print(str(datetime.datetime.now())[:19], "Starting with File: ", args.infile)

    tmp_txt = 'tmp/ground_temp.las'
    cc_file = 'tmp/Data_Lans_HighDensity_Params.txt'

    if args.clip:
        xmin = args.extent.split()[0]
        ymin = args.extent.split()[1]
        xmax = args.extent.split()[2]
        ymax = args.extent.split()[3]


def main(infile, cc_file, final_out, method, clip, crater_shp, xmin=0, ymin=0, xmax=0, ymax=0):

    if method == "Filter":

        if clip:
            cc_cmd_filter(infile, cc_file, xmin, ymin, 0, xmax, ymax, 3000, clip)
        else:
            cc_cmd_filter(infile, cc_file, clip)
        print(str(datetime.datetime.now())[:19], 'Step 1 of 6 - PointCloud clipped to AOI and Attributes calculated')
        filter_df = filter(cc_file)

    elif method == "DecisionTree":

        if clip:
            cc_cmd_ml(infile, cc_file, xmin, ymin, 0, xmax, ymax, 3000, clip)
        else:
            cc_cmd_ml(infile, cc_file, clip)
            df = pd.read_csv(cc_file, sep=";")
            df = df.rename(columns={'//X': 'X'})
            df = df.dropna(how='any', axis=0)
            df_pred = df.drop(['X', 'Y', 'Z', 'Nx', 'Ny', 'Nz'], axis=1)
            print(str(datetime.datetime.now())[:19], 'Step 1 of 6 - PointCloud clipped to AOI and Attributes calculated')

            loaded_model = pickle.load(open('Models/DecisionTreeClassifier.sav', 'rb'))
            prediction = loaded_model.predict(df_pred)

            df['Prediction'] = prediction
            print('Points labeld as craters: ', sum(prediction))
            filter_df = df[df.Prediction == 1]
            remaining_df = df[df.Prediction != 1]

    elif method == "RandomForest":

        if clip:
            cc_cmd_ml(infile, cc_file, xmin, ymin, 0, xmax, ymax, 3000, clip)
        else:
            cc_cmd_ml(infile, cc_file, clip)
            df = pd.read_csv(cc_file, sep=";")
            df = df.rename(columns={'//X': 'X'})
            df = df.dropna(how='any', axis=0)
            df_pred = df.drop(['X', 'Y', 'Z', 'Nx', 'Ny', 'Nz'], axis=1)
            print(str(datetime.datetime.now())[:19], 'Step 1 of 6 - PointCloud clipped to AOI and Attributes calculated')

            loaded_model = pickle.load(open('Models/RandomForestClassifier.sav', 'rb'))
            prediction = loaded_model.predict(df_pred)

            df['Prediction'] = prediction
            print('Points labeld as craters: ', sum(prediction))
            filter_df = df[df.Prediction == 1]
            remaining_df = df[df.Prediction != 1]

    print(str(datetime.datetime.now())[:19], 'Step 2 of 6 - PointCloud classified by ', str(args.method))

    segmented = region_growing(filter_df)
    print(str(datetime.datetime.now())[:19], 'Step 3 of 6 - PointCloud segmented by Connected Components')
    segmented.to_csv("tmp/segmented.txt", sep=";", index=False)
    filtered = filter_segments(segmented)
    print(str(datetime.datetime.now())[:19], 'Step 4 of 6 - Segments filtered for Craters')
    filtered.to_csv("tmp/filtered.txt", sep=";", index=False)

    seed_df = find_seeds(filtered, cc_file)
    craters = segment_craters(seed_df, cc_file)

    print(str(datetime.datetime.now())[:19], 'Step 5 of 6 - Craters Classified and Segmented')
    classified_pc = pd.concat([craters, remaining_df], ignore_index=True)
    classified_pc.to_csv(final_out, sep=';', index=False)

    bounding_box.draw_bb(craters, crater_shp)
    print(str(datetime.datetime.now())[:19], "Step 6 of 6 - Bounding Box shp created")

    if not args.keep_tmp:
        delete_contents('tmp')


if __name__ == "__main__":

    main(args.infile, cc_file, args.outfile, args.method, args.clip, args.out_shp, xmin=0, ymin=0, xmax=0, ymax=0)